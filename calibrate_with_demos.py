#!/usr/bin/env python3
"""
calibrate_with_demos.py — Calibrate ML threshold using Normal vs Demo "Bad"

Why:
  IsolationForest is unsupervised, so the main lever for false positives is the
  calibrated anomaly threshold (and consecutive-hits). This script:
    1) Loads the current production model bundle at MODEL_PATH (baseline.pkl)
    2) Collects "normal" samples from your real machine for a duration
    3) Scores built-in demo scenario feature vectors (mirrors run_all_demos.sh intent)
    4) Chooses a threshold that meets a target false-positive-rate (FPR) on normal
       while maximizing detection rate on demo scenarios
    5) Writes the chosen threshold back into the saved model bundle (with backup)

Safe:
  - Does NOT retrain the model.
  - Only updates the stored threshold value used by AnomalyDetector.

Usage examples:
  python3 calibrate_with_demos.py --minutes 60 --target-fpr 0.001
  python3 calibrate_with_demos.py --minutes 120 --target-fpr 0.0005
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from config import MODEL_PATH
from config import ML_ANOMALY_CONSECUTIVE_HITS, MONITORING_INTERVAL_SECONDS
from agent.monitor import collect_snapshot


def _load_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model bundle not found at {MODEL_PATH}")
    loaded = joblib.load(MODEL_PATH)
    if not isinstance(loaded, dict) or "pipeline" not in loaded:
        raise ValueError(
            "Expected a v2 model bundle dict with key 'pipeline'. "
            "If you have a legacy model, retrain once by running main.py."
        )
    return loaded


def _collect_normal_vectors(minutes: float, interval_seconds: float = 5.0) -> np.ndarray:
    end = time.time() + (minutes * 60.0)
    xs: list[list[float]] = []
    while time.time() < end:
        snap = collect_snapshot()
        xs.append(snap.to_feature_vector())
        time.sleep(interval_seconds)
    return np.array(xs, dtype=float)


def _demo_vectors() -> np.ndarray:
    """
    Feature vectors aligned to SystemSnapshot.to_feature_vector():
      [cpu, mem, num_processes, num_connections, num_listening_ports, new_conns, file_events]

    These vectors represent the "bad" behaviours simulated by run_all_demos.sh
    (CPU spike, RAM spike, connection burst, file tampering).
    """
    demos = [
        # HIGH_CPU-like
        [65.0, 45.0, 150.0, 0.0, 0.0, 0.0, 0.0],
        # HIGH_MEMORY-like
        [15.0, 91.5, 150.0, 0.0, 0.0, 0.0, 0.0],
        # SUSPICIOUS_PORT-like (connection present)
        [8.0, 50.0, 150.0, 1.0, 0.0, 1.0, 0.0],
        # BLACKLISTED_IP-like (connection present)
        [5.0, 48.0, 150.0, 1.0, 0.0, 1.0, 0.0],
        # Sensitive file write burst
        [3.0, 40.0, 150.0, 0.0, 0.0, 0.0, 3.0],
        # Sensitive file delete burst
        [2.0, 35.0, 150.0, 0.0, 0.0, 0.0, 3.0],
        # Rapid connections / port scanning (connection burst)
        [25.0, 55.0, 150.0, 50.0, 0.0, 50.0, 0.0],
        # Multi-stage chain (blend)
        [85.0, 65.0, 170.0, 30.0, 0.0, 30.0, 0.0],
        [15.0, 60.0, 160.0, 2.0, 0.0, 2.0, 0.0],
    ]
    return np.array(demos, dtype=float)


def _score(pipeline, X: np.ndarray) -> np.ndarray:
    # IsolationForest score_samples: higher = more normal, lower = more anomalous
    return np.array(pipeline.score_samples(X), dtype=float)


def _choose_threshold(normal_scores: np.ndarray, demo_scores: np.ndarray, target_fpr: float) -> tuple[float, dict]:
    """
    Pick threshold T such that:
      FPR = P(score < T | normal) <= target_fpr
    and detection on demos (P(score < T | demo)) is maximized.
    """
    target_fpr = float(target_fpr)
    target_fpr = min(max(target_fpr, 1e-6), 0.2)

    # Candidate thresholds from normal quantiles (low tail)
    qs = np.array([1e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2], dtype=float)
    candidates = np.unique(np.quantile(normal_scores, qs))

    best = None
    best_meta = {}
    for T in candidates:
        fpr = float(np.mean(normal_scores < T))
        if fpr > target_fpr:
            continue
        tpr = float(np.mean(demo_scores < T))
        # Prefer higher TPR; tie-break with lower FPR
        score = (tpr, -fpr)
        if best is None or score > best:
            best = score
            best_meta = {"threshold": float(T), "fpr": fpr, "demo_detection": tpr}

    # If nothing meets target FPR, fall back to exact quantile threshold.
    if not best_meta:
        T = float(np.quantile(normal_scores, target_fpr))
        best_meta = {
            "threshold": T,
            "fpr": float(np.mean(normal_scores < T)),
            "demo_detection": float(np.mean(demo_scores < T)),
            "note": "No candidate met target_fpr; used exact normal quantile.",
        }

    return float(best_meta["threshold"]), best_meta


def _target_fpr_from_alerts_per_day(
    alerts_per_day: float,
    interval_seconds: float,
    consecutive_hits: int,
) -> float:
    """
    Convert a target "false alerts per day" into a per-snapshot FPR target.

    Approximation:
      expected_alerts/day ≈ N * p^k
      where:
        N = snapshots/day (86400 / interval_seconds)
        p = per-snapshot probability of scoring below threshold (FPR)
        k = consecutive hits required

    This is a pragmatic calibration target (real systems have temporal correlation).
    """
    k = max(1, int(consecutive_hits))
    n = max(1.0, 86400.0 / max(0.5, float(interval_seconds)))
    a = max(1e-9, float(alerts_per_day))
    p = (a / n) ** (1.0 / k)
    return float(min(max(p, 1e-6), 0.2))


def main():
    ap = argparse.ArgumentParser(description="Calibrate IsolationForest threshold using normal vs demo data")
    ap.add_argument("--minutes", type=float, default=60.0, help="Minutes to collect normal samples (default: 60)")
    ap.add_argument("--interval", type=float, default=5.0, help="Seconds between normal samples (default: 5)")
    ap.add_argument(
        "--target-fpr",
        type=float,
        default=None,
        help="Target per-snapshot false positive rate on normal (advanced). If omitted, derived from --target-alerts-per-day.",
    )
    ap.add_argument(
        "--target-alerts-per-day",
        type=float,
        default=1.0,
        help="Target false ML alerts per day (default: 1.0). Used to derive per-snapshot FPR target.",
    )
    ap.add_argument("--write", action="store_true", help="Actually write calibrated threshold into baseline.pkl")
    args = ap.parse_args()

    bundle = _load_bundle()
    pipeline = bundle["pipeline"]

    hits = int(ML_ANOMALY_CONSECUTIVE_HITS)
    effective_interval = float(args.interval) if args.interval else float(MONITORING_INTERVAL_SECONDS)
    derived_fpr = _target_fpr_from_alerts_per_day(
        alerts_per_day=float(args.target_alerts_per_day),
        interval_seconds=effective_interval,
        consecutive_hits=hits,
    )
    target_fpr = float(args.target_fpr) if args.target_fpr is not None else derived_fpr

    print(f"Loading model: {MODEL_PATH}")
    print(f"Collecting normal samples for {args.minutes:.1f} minutes (interval {args.interval:.1f}s)…")
    Xn = _collect_normal_vectors(minutes=args.minutes, interval_seconds=args.interval)
    if Xn.size == 0:
        raise RuntimeError("No normal samples collected.")

    Xd = _demo_vectors()

    sn = _score(pipeline, Xn)
    sd = _score(pipeline, Xd)

    T, meta = _choose_threshold(sn, sd, target_fpr=target_fpr)

    print("\n=== Calibration summary ===")
    print(f"Normal samples: {len(sn)}")
    print(f"Demo samples:   {len(sd)}")
    print(f"Current threshold: {float(bundle.get('threshold', float('nan'))):.6f}")
    print(f"Chosen  threshold: {T:.6f}")
    print(f"Consecutive hits required: {hits}")
    print(f"Target false alerts/day:   {float(args.target_alerts_per_day):.3f}")
    print(f"Target per-snapshot FPR:   {target_fpr:.6f}")
    print(f"Estimated normal FPR: {meta.get('fpr'):.6f} (target {target_fpr:.6f})")
    print(f"Demo detection rate:  {meta.get('demo_detection'):.3f}")
    if meta.get("note"):
        print(f"Note: {meta['note']}")

    if not args.write:
        print("\nDry run. Re-run with --write to persist the threshold.")
        return

    # Backup and write
    backup = MODEL_PATH.with_suffix(".pkl.backup")
    if not backup.exists():
        joblib.dump(bundle, backup)
        print(f"Backup written: {backup}")

    bundle["threshold"] = float(T)
    bundle["calibrated_at"] = time.time()
    bundle["calibration"] = {
        "target_false_alerts_per_day": float(args.target_alerts_per_day),
        "target_fpr": float(target_fpr),
        "consecutive_hits": int(hits),
        "interval_seconds": float(effective_interval),
        "normal_samples": int(len(sn)),
        "demo_samples": int(len(sd)),
        "normal_score_stats": {
            "min": float(np.min(sn)),
            "p01": float(np.quantile(sn, 0.01)),
            "p05": float(np.quantile(sn, 0.05)),
            "median": float(np.median(sn)),
            "p95": float(np.quantile(sn, 0.95)),
            "max": float(np.max(sn)),
        },
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"Updated model threshold saved: {MODEL_PATH}")


if __name__ == "__main__":
    main()

