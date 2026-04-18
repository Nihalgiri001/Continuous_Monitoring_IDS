"""
ml_engine/explainability.py — Explainable AI Threat Analysis

Goal:
  When an ML anomaly is detected, produce operator-friendly reasons such as:
    - CPU spike
    - RAM spike
    - suspicious outbound connections
    - rare process behaviour (top CPU/MEM consumers)
    - file tampering activity

Implementation notes:
  - SHAP is attempted (preferred) when available, but is optional.
  - A deterministic heuristic explanation is always generated as a fallback,
    because alerting must not depend on heavy explainability libs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from config import CPU_ALERT_THRESHOLD, MEMORY_ALERT_THRESHOLD, RAPID_CONNECTION_THRESHOLD

logger = logging.getLogger(__name__)


FEATURE_NAMES: list[str] = [
    "cpu_percent",
    "memory_percent",
    "num_processes",
    "num_connections",
    "num_listening_ports",
    "num_new_connections",
    "num_file_events",
]


@dataclass(frozen=True)
class ThreatExplanation:
    reasons: list[str]
    feature_contributions: list[dict[str, Any]]  # [{name, value, impact}]
    method: str  # "shap" | "heuristic"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _top_process_summaries(processes: list[dict] | None, top_n: int = 3) -> list[str]:
    if not processes:
        return []
    procs = []
    for p in processes:
        try:
            procs.append(
                {
                    "pid": p.get("pid"),
                    "name": p.get("name") or "unknown",
                    "cpu": _safe_float(p.get("cpu_percent"), 0.0),
                    "mem": _safe_float(p.get("memory_percent"), 0.0),
                }
            )
        except Exception:
            continue
    procs.sort(key=lambda d: (d["cpu"], d["mem"]), reverse=True)
    out = []
    for p in procs[:top_n]:
        out.append(f"{p['name']} (PID {p['pid']}) CPU {p['cpu']:.1f}% MEM {p['mem']:.1f}%")
    return out


def _outbound_ip_summaries(connections: list[dict] | None, top_n: int = 5) -> tuple[int, list[str]]:
    if not connections:
        return 0, []
    ips: dict[str, int] = {}
    for c in connections:
        raddr = c.get("raddr") or ""
        if not raddr or ":" not in raddr:
            continue
        ip = raddr.split(":")[0]
        if not ip:
            continue
        ips[ip] = ips.get(ip, 0) + 1
    top = sorted(ips.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return len(ips), [f"{ip} ({cnt} conns)" for ip, cnt in top]


def _file_event_summary(file_events: list[dict] | None, top_n: int = 5) -> list[str]:
    if not file_events:
        return []
    out = []
    for fe in file_events[:top_n]:
        try:
            t = fe.get("type") or "event"
            src = fe.get("src") or ""
            dest = fe.get("dest") or ""
            if dest:
                out.append(f"{t}: {src} → {dest}")
            else:
                out.append(f"{t}: {src}")
        except Exception:
            continue
    return out


def _heuristic_explain(snapshot_context: dict[str, Any], feature_vector: list[float]) -> ThreatExplanation:
    cpu = _safe_float(feature_vector[0] if len(feature_vector) > 0 else None)
    mem = _safe_float(feature_vector[1] if len(feature_vector) > 1 else None)
    new_conns = int(_safe_float(feature_vector[5] if len(feature_vector) > 5 else 0.0))
    num_files = int(_safe_float(feature_vector[6] if len(feature_vector) > 6 else 0.0))

    reasons: list[str] = []
    contributions: list[dict[str, Any]] = []

    # CPU spike
    if cpu >= max(90.0, float(CPU_ALERT_THRESHOLD)):
        reasons.append(f"CPU usage {cpu:.1f}%")
        contributions.append({"name": "cpu_percent", "value": cpu, "impact": "high"})

    # RAM spike
    if mem >= max(90.0, float(MEMORY_ALERT_THRESHOLD)):
        reasons.append(f"RAM usage {mem:.1f}%")
        contributions.append({"name": "memory_percent", "value": mem, "impact": "high"})

    # Suspicious outbound connections
    if new_conns >= int(max(15, int(RAPID_CONNECTION_THRESHOLD))):
        reasons.append(f"Connection burst: {new_conns} new outbound connections")
        contributions.append({"name": "num_new_connections", "value": new_conns, "impact": "high"})

    # Rare process behaviour (top offenders)
    top_procs = _top_process_summaries(snapshot_context.get("processes"), top_n=3)
    if top_procs:
        # Include the top process if it's notable
        notable = [p for p in top_procs if ("CPU" in p or "MEM" in p)]
        if notable and (cpu >= 70 or mem >= 70):
            reasons.append("Top resource-consuming processes: " + "; ".join(top_procs))
            contributions.append({"name": "processes", "value": top_procs, "impact": "medium"})

    # File tampering
    file_summ = _file_event_summary(snapshot_context.get("file_events"), top_n=5)
    if num_files > 0 and file_summ:
        reasons.append(f"File activity detected ({num_files} events): " + "; ".join(file_summ))
        contributions.append({"name": "num_file_events", "value": num_files, "impact": "medium"})

    # Suspicious outbound IP diversity
    uniq_ips, top_ips = _outbound_ip_summaries(snapshot_context.get("connections"), top_n=5)
    if uniq_ips >= 10:
        reasons.append(f"Unusual outbound IP diversity: {uniq_ips} unique remote IPs")
        contributions.append({"name": "remote_ip_diversity", "value": uniq_ips, "impact": "medium"})
        if top_ips:
            reasons.append("Top remote IPs: " + ", ".join(top_ips))

    if not reasons:
        reasons.append("Anomalous system behaviour detected (no single dominant factor)")

    return ThreatExplanation(reasons=reasons, feature_contributions=contributions, method="heuristic")


def _try_shap_explain(model: Any, feature_vector: list[float]) -> ThreatExplanation | None:
    """
    Best-effort SHAP explanation.
    Returns None if SHAP is unavailable or the model isn't supported.
    """
    try:
        import shap  # type: ignore
    except Exception:
        return None

    try:
        # Prefer using the IsolationForest estimator inside a pipeline.
        estimator = model
        if hasattr(model, "named_steps") and "iforest" in getattr(model, "named_steps", {}):
            estimator = model.named_steps["iforest"]

        x = np.array(feature_vector, dtype=float).reshape(1, -1)

        # TreeExplainer is fastest; it may still fail for IsolationForest on some SHAP versions.
        explainer = shap.TreeExplainer(estimator)
        sv = explainer.shap_values(x)
        # sv can be list-like; normalize to 1d float array
        sv_arr = np.array(sv).reshape(-1)
        impacts = np.abs(sv_arr)
        order = np.argsort(-impacts)[:5]
        contributions: list[dict[str, Any]] = []
        for idx in order:
            name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"f{idx}"
            contributions.append(
                {
                    "name": name,
                    "value": float(x[0, idx]) if idx < x.shape[1] else None,
                    "impact": float(sv_arr[idx]),
                }
            )

        # Convert top contributions to human reasons (keep it simple and readable).
        reasons: list[str] = []
        for c in contributions:
            n = c["name"]
            v = c["value"]
            if n == "cpu_percent" and v is not None:
                reasons.append(f"CPU usage {float(v):.1f}%")
            elif n == "memory_percent" and v is not None:
                reasons.append(f"RAM usage {float(v):.1f}%")
            elif n == "num_new_connections" and v is not None:
                reasons.append(f"New outbound connections {int(float(v))}")
            elif n == "num_connections" and v is not None:
                reasons.append(f"Total active connections {int(float(v))}")
            elif n == "num_file_events" and v is not None:
                reasons.append(f"File events observed {int(float(v))}")
            elif v is not None:
                reasons.append(f"{n}={v}")

        if not reasons:
            reasons = ["Anomalous system behaviour detected (SHAP)"]

        return ThreatExplanation(reasons=reasons, feature_contributions=contributions, method="shap")
    except Exception as exc:
        logger.debug("SHAP explanation failed: %s", exc)
        return None


class ExplainableThreatAnalyzer:
    def explain_ml_anomaly(
        self,
        model: Any,
        feature_vector: list[float],
        snapshot_context: dict[str, Any] | None = None,
    ) -> ThreatExplanation:
        snapshot_context = snapshot_context or {}

        shap_exp = _try_shap_explain(model, feature_vector)
        if shap_exp is not None:
            # Enrich SHAP output with extra operator context when available.
            extra_reasons = []
            top_procs = _top_process_summaries(snapshot_context.get("processes"), top_n=3)
            if top_procs:
                extra_reasons.append("Top processes: " + "; ".join(top_procs))
            uniq_ips, top_ips = _outbound_ip_summaries(snapshot_context.get("connections"), top_n=5)
            if uniq_ips:
                extra_reasons.append(f"Remote IPs: {uniq_ips} unique (" + ", ".join(top_ips) + ")")
            file_summ = _file_event_summary(snapshot_context.get("file_events"), top_n=5)
            if file_summ:
                extra_reasons.append("File activity: " + "; ".join(file_summ))

            return ThreatExplanation(
                reasons=shap_exp.reasons + extra_reasons,
                feature_contributions=shap_exp.feature_contributions,
                method="shap",
            )

        return _heuristic_explain(snapshot_context, feature_vector)

