"""
core/severity.py — Severity Scoring System

Defines a four-tier severity model (LOW → CRITICAL) and maps
every rule ID to its severity level. New rules must be registered here.
"""

from enum import Enum


class Severity(str, Enum):
    LOW      = "Low"
    MEDIUM   = "Medium"
    HIGH     = "High"
    CRITICAL = "Critical"
    ANOMALY  = "Anomaly"   # ML-detected, severity TBD by score

    def __lt__(self, other):
        return _ORDER[self] < _ORDER[other]

    def __le__(self, other):
        return _ORDER[self] <= _ORDER[other]

    def __gt__(self, other):
        return _ORDER[self] > _ORDER[other]

    def __ge__(self, other):
        return _ORDER[self] >= _ORDER[other]

    @property
    def color(self) -> str:
        """Rich/ANSI color name for console output."""
        return _COLORS[self]

    @property
    def emoji(self) -> str:
        return _EMOJIS[self]

    @property
    def score(self) -> int:
        """Numeric score (useful for sorting/comparison)."""
        return _ORDER[self]


_ORDER: dict = {
    Severity.LOW:      1,
    Severity.MEDIUM:   2,
    Severity.HIGH:     3,
    Severity.CRITICAL: 4,
    Severity.ANOMALY:  2,   # treat as medium until calibrated
}

_COLORS: dict = {
    Severity.LOW:      "green",
    Severity.MEDIUM:   "yellow",
    Severity.HIGH:     "red",
    Severity.CRITICAL: "bold red",
    Severity.ANOMALY:  "magenta",
}

_EMOJIS: dict = {
    Severity.LOW:      "🟢",
    Severity.MEDIUM:   "🟡",
    Severity.HIGH:     "🔴",
    Severity.CRITICAL: "💀",
    Severity.ANOMALY:  "🤖",
}


# ── Severity map: rule_id → Severity ──────────────────────────────────────────
# Extend this dict whenever you add a new detection rule.

SEVERITY_MAP: dict[str, Severity] = {
    # Process rules
    "HIGH_CPU":               Severity.MEDIUM,
    "HIGH_MEMORY":            Severity.MEDIUM,
    "BLACKLISTED_PROCESS":    Severity.HIGH,
    "ROOT_SHELL_SPAWN":       Severity.CRITICAL,

    # Network rules
    "BLACKLISTED_IP":         Severity.HIGH,
    "SUSPICIOUS_PORT":        Severity.HIGH,
    "RAPID_CONNECTIONS":      Severity.MEDIUM,
    "MALICIOUS_DOMAIN":       Severity.HIGH,

    # File system rules
    "SENSITIVE_FILE_WRITE":   Severity.HIGH,
    "SENSITIVE_FILE_DELETE":  Severity.CRITICAL,
    "SENSITIVE_FILE_CREATE":  Severity.MEDIUM,

    # Vulnerability scanner
    "OPEN_RISKY_PORT":        Severity.HIGH,
    "WEAK_SSH_CONFIG":        Severity.HIGH,
    "WORLD_WRITABLE_PATH":    Severity.MEDIUM,
    "FIREWALL_DISABLED":      Severity.CRITICAL,
    "OPEN_PORT":              Severity.LOW,

    # ML engine
    "ML_ANOMALY":             Severity.ANOMALY,
}


def get_severity(rule_id: str) -> Severity:
    """Look up severity for a rule. Defaults to MEDIUM for unknown rules."""
    return SEVERITY_MAP.get(rule_id, Severity.MEDIUM)


__all__ = ["Severity", "SEVERITY_MAP", "get_severity"]
