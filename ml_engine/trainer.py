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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ML_WARMUP_SAMPLES, ML_CONTAMINATION, MODEL_PATH, ML_ANOMALY_SCORE_QUANTILE
from core.event_queue import event_queue, safe_get
from core.threat_event import SystemSnapshot

logger = logging.getLogger(__name__)

MODEL_VERSION = 2


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

    def _train(self) -> dict:
        X = np.array(self._samples)
        pipeline = Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "iforest",
                    IsolationForest(
                        n_estimators=200,
                        contamination=ML_CONTAMINATION,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
        pipeline.fit(X)

        # score_samples: higher = more normal, lower = more anomalous
        scores = pipeline.score_samples(X)
        q = float(ML_ANOMALY_SCORE_QUANTILE)
        q = min(max(q, 1e-6), 0.2)  # guardrails against misconfig
        calibrated_threshold = float(np.quantile(scores, q))

        return {
            "version": MODEL_VERSION,
            "pipeline": pipeline,
            "threshold": calibrated_threshold,
            "score_quantile": q,
            "score_stats": {
                "min": float(np.min(scores)),
                "p01": float(np.quantile(scores, 0.01)),
                "p05": float(np.quantile(scores, 0.05)),
                "median": float(np.median(scores)),
                "p95": float(np.quantile(scores, 0.95)),
                "max": float(np.max(scores)),
            },
            "trained_on_samples": int(X.shape[0]),
            "n_features": int(X.shape[1]) if X.ndim == 2 else 0,
            "trained_at": time.time(),
        }

    def run(self):
        self._collect_samples()
        if self._stop_event.is_set():
            return

        logger.info("Training IsolationForest on %d samples…", len(self._samples))
        try:
            model_bundle = self._train()
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model_bundle, MODEL_PATH)
            logger.info(
                "✅ ML model trained & saved → %s (threshold=%.4f, q=%.4f)",
                MODEL_PATH,
                model_bundle.get("threshold", float("nan")),
                model_bundle.get("score_quantile", float("nan")),
            )
            self.trained.set()
        except Exception as exc:
            logger.error("ML training failed: %s", exc, exc_info=True)


def load_model() -> dict | IsolationForest | None:
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            logger.warning("Could not load existing model: %s", e)
    return None


__all__ = ["ModelTrainer", "load_model"]
