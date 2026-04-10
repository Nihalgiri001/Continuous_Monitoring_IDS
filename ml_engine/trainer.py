"""
ml_engine/trainer.py — IsolationForest Baseline Trainer

Collects system snapshots during a warm-up window, trains an
IsolationForest on normal behaviour, then persists the model to disk.
"""

import logging
import threading
import time
import joblib
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ML_WARMUP_SAMPLES, ML_CONTAMINATION, MODEL_PATH
from core.event_queue import event_queue, safe_get
from core.threat_event import SystemSnapshot

logger = logging.getLogger(__name__)


class ModelTrainer(threading.Thread):
    """
    Phase 1: warm-up — collects ML_WARMUP_SAMPLES snapshots.
    Phase 2: trains IsolationForest on collected vectors.
    Phase 3: saves model to MODEL_PATH and signals completion.
    """

    daemon = True

    def __init__(self):
        super().__init__(name="ModelTrainer")
        self._samples: list[list[float]] = []
        self.trained = threading.Event()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    # Peek at queue items without consuming them permanently
    def _collect_samples(self):
        logger.info(
            "ML warm-up: collecting %d baseline snapshots…", ML_WARMUP_SAMPLES
        )
        while len(self._samples) < ML_WARMUP_SAMPLES and not self._stop_event.is_set():
            snap = safe_get(event_queue, timeout=2.0)
            if snap is None:
                continue
            if not isinstance(snap, SystemSnapshot):
                # Put non-snapshots back so the rules engine can see them
                event_queue.put(snap)
                continue
            vec = snap.to_feature_vector()
            self._samples.append(vec)
            # Re-enqueue the snapshot so the rules engine also processes it
            event_queue.put(snap)
            logger.debug("Warm-up sample %d/%d", len(self._samples), ML_WARMUP_SAMPLES)

    def _train(self) -> IsolationForest:
        X = np.array(self._samples)
        model = IsolationForest(
            n_estimators=100,
            contamination=ML_CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X)
        return model

    def run(self):
        self._collect_samples()
        if self._stop_event.is_set():
            return

        logger.info("Training IsolationForest on %d samples…", len(self._samples))
        try:
            model = self._train()
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, MODEL_PATH)
            logger.info("✅ ML model trained & saved → %s", MODEL_PATH)
            self.trained.set()
        except Exception as exc:
            logger.error("ML training failed: %s", exc, exc_info=True)


def load_model() -> IsolationForest | None:
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            logger.warning("Could not load existing model: %s", e)
    return None


__all__ = ["ModelTrainer", "load_model"]
