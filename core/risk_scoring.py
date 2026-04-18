"""
core/risk_scoring.py — Dynamic Risk Scoring Engine (0–100)

Computes a risk score per ThreatEvent based on:
  - ML anomaly score (if present)
  - rule-based severity
  - blacklisted IP/process hit
  - dangerous open ports
  - privilege escalation attempt
  - repeated suspicious behaviour (bursting)

Outputs:
  - score: 0..100
  - label: Low/Medium/High/Critical using project thresholds
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from core.severity import Severity


@dataclass(frozen=True)
class RiskScore:
    score: int
    label: str  # Low | Medium | High | Critical
    breakdown: dict[str, int]


def _clamp_int(v: float, lo: int, hi: int) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = lo
    return max(lo, min(hi, iv))


def _label_for(score: int) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def _severity_weight(sev: Severity) -> int:
    return {
        Severity.LOW: 10,
        Severity.MEDIUM: 25,
        Severity.HIGH: 45,
        Severity.CRITICAL: 70,
        Severity.ANOMALY: 30,
    }.get(sev, 25)


def _ml_score_to_risk(ml_score: float | None, threshold: float | None) -> int:
    """
    IsolationForest score_samples: higher = more normal, lower = more anomalous.
    Convert to a 0..40 component where deeper below threshold increases risk.
    """
    if ml_score is None or threshold is None:
        return 0
    try:
        score = float(ml_score)
        th = float(threshold)
    except Exception:
        return 0

    # If score is just below threshold: small risk; far below: bigger.
    delta = max(0.0, th - score)
    # Typical score ranges are small; scale with a soft cap.
    return _clamp_int(min(40.0, delta * 200.0), 0, 40)


class RepetitionTracker:
    """
    Tracks repeated suspicious behaviours in a rolling time window.
    Used to boost risk when the same key is seen repeatedly.
    """

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = int(window_seconds)
        self._events: dict[str, list[float]] = {}

    def record_and_count(self, key: str) -> int:
        now = time.time()
        xs = self._events.get(key, [])
        xs.append(now)
        cutoff = now - self.window_seconds
        xs = [t for t in xs if t >= cutoff]
        self._events[key] = xs
        return len(xs)


class RiskScoringEngine:
    def __init__(self, repetition_window_seconds: int = 300):
        self._tracker = RepetitionTracker(window_seconds=repetition_window_seconds)

    def _event_key(self, event) -> str:
        rd = getattr(event, "raw_data", {}) or {}
        discriminator = (
            rd.get("pid")
            or rd.get("raddr")
            or rd.get("port")
            or rd.get("src")
            or rd.get("name")
            or ""
        )
        return f"{getattr(event, 'rule_id', 'UNKNOWN')}::{discriminator}"

    def score(self, event) -> RiskScore:
        rd: dict[str, Any] = getattr(event, "raw_data", {}) or {}

        breakdown: dict[str, int] = {}

        # Base from rule severity
        sev = getattr(event, "severity", Severity.MEDIUM)
        breakdown["rule_severity"] = _severity_weight(sev)

        # ML component
        ml_score = None
        threshold = None
        if event.rule_id == "ML_ANOMALY":
            ml_score = rd.get("ml_score")
            threshold = rd.get("threshold")
        breakdown["ml_anomaly"] = _ml_score_to_risk(ml_score, threshold)

        # Blacklist hits
        if event.rule_id in ("BLACKLISTED_IP", "BLACKLISTED_PROCESS"):
            breakdown["blacklist_hit"] = 20
        else:
            breakdown["blacklist_hit"] = 0

        # Dangerous open ports
        if event.rule_id in ("OPEN_RISKY_PORT", "SUSPICIOUS_PORT"):
            breakdown["dangerous_port"] = 15
        else:
            breakdown["dangerous_port"] = 0

        # Privilege escalation attempt
        if event.rule_id in ("ROOT_SHELL_SPAWN",):
            breakdown["privilege_escalation"] = 30
        else:
            breakdown["privilege_escalation"] = 0

        # File tampering
        if event.rule_id in ("SENSITIVE_FILE_DELETE", "SENSITIVE_FILE_WRITE", "SENSITIVE_FILE_CREATE"):
            breakdown["file_tampering"] = 15
        else:
            breakdown["file_tampering"] = 0

        # Repeated suspicious behavior boost
        count = self._tracker.record_and_count(self._event_key(event))
        if count >= 5:
            breakdown["repetition"] = 20
        elif count >= 3:
            breakdown["repetition"] = 10
        else:
            breakdown["repetition"] = 0

        total = sum(breakdown.values())
        score = _clamp_int(total, 0, 100)
        return RiskScore(score=score, label=_label_for(score), breakdown=breakdown)


__all__ = ["RiskScoringEngine", "RiskScore"]

