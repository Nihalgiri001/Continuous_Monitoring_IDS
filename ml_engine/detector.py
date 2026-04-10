"""
ml_engine/detector.py — Live Anomaly Detection

Loads a trained IsolationForest model and scores every incoming
snapshot. Anomalous snapshots trigger ML_ANOMALY ThreatEvents.
"""

import logging
import threading
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ML_ANOMALY_SCORE_THRESHOLD
from core.event_queue import event_queue, threat_queue, safe_get, safe_put
from core.threat_event import ThreatEvent, SystemSnapshot
from ml_engine.trainer import load_model, ModelTrainer

logger = logging.getLogger(__name__)


class AnomalyDetector(threading.Thread):
    """
    Waits for the ML model to be ready, then scores every snapshot.
    Runs concurrently with — not instead of — the rules engine.
    """

    daemon = True

    def __init__(self, trainer: ModelTrainer):
        super().__init__(name="AnomalyDetector")
        self._trainer = trainer
        self._model = None
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def _wait_for_model(self):
        # Try loading pre-existing model first
        self._model = load_model()
        if self._model is not None:
            logger.info("AnomalyDetector: loaded pre-existing model")
            return
        logger.info("AnomalyDetector: waiting for warm-up training to complete…")
        self._trainer.trained.wait()
        self._model = load_model()
        if self._model is None:
            logger.error("AnomalyDetector: model still unavailable after training")

    def _score_snapshot(self, snap: SystemSnapshot) -> float:
        """Returns IsolationForest anomaly score (negative = more anomalous)."""
        vec = np.array(snap.to_feature_vector()).reshape(1, -1)
        return float(self._model.score_samples(vec)[0])

    def run(self):
        self._wait_for_model()
        if self._model is None:
            logger.warning("AnomalyDetector disabled — no model available")
            return

        logger.info("AnomalyDetector active, threshold=%.3f", ML_ANOMALY_SCORE_THRESHOLD)
        while not self._stop_event.is_set():
            snap = safe_get(event_queue, timeout=1.0)
            if snap is None:
                continue
            if not isinstance(snap, SystemSnapshot):
                event_queue.put(snap)
                continue

            try:
                score = self._score_snapshot(snap)
                logger.debug("ML score: %.4f", score)

                if score < ML_ANOMALY_SCORE_THRESHOLD:
                    fv = snap.to_feature_vector()
                    evt = ThreatEvent(
                        rule_id="ML_ANOMALY",
                        description=(
                            f"Anomaly detected by ML engine (score={score:.4f}). "
                            f"CPU={fv[0]:.1f}% MEM={fv[1]:.1f}% "
                            f"PROCS={int(fv[2])} CONNS={int(fv[3])}"
                        ),
                        raw_data={
                            "ml_score": score,
                            "feature_vector": fv,
                            "threshold": ML_ANOMALY_SCORE_THRESHOLD,
                        },
                        source="ml_engine",
                    )
                    safe_put(threat_queue, evt)
                    logger.info("[ML ANOMALY] score=%.4f — %s", score, evt.description)

            except Exception as exc:
                logger.error("AnomalyDetector scoring error: %s", exc)

            # Re-enqueue for the rules engine if it hasn't been processed yet
            # (Both engines share the same queue — the rules engine drains it faster)
            # NOTE: to avoid double-processing, use separate queues in production.

        logger.info("AnomalyDetector stopped")


__all__ = ["AnomalyDetector"]
