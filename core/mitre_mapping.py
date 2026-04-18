"""
core/mitre_mapping.py — MITRE ATT&CK mapping for detections

Maps CyberCBP rule IDs to MITRE ATT&CK tactics (and optional techniques).
This is a pragmatic mapping for operator context (not a full technique taxonomy).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MitreMapping:
    tactic: str
    technique: str | None = None


# Tactics reference:
# - Reconnaissance
# - Resource Development
# - Initial Access
# - Execution
# - Persistence
# - Privilege Escalation
# - Defense Evasion
# - Credential Access
# - Discovery
# - Lateral Movement
# - Collection
# - Command and Control
# - Exfiltration
# - Impact

MITRE_MAP: dict[str, MitreMapping] = {
    # Network / recon patterns
    "RAPID_CONNECTIONS": MitreMapping(tactic="Reconnaissance"),
    "OPEN_PORT": MitreMapping(tactic="Discovery"),
    "OPEN_RISKY_PORT": MitreMapping(tactic="Discovery"),
    "SUSPICIOUS_PORT": MitreMapping(tactic="Command and Control"),
    "BLACKLISTED_IP": MitreMapping(tactic="Command and Control"),

    # Process / execution
    "BLACKLISTED_PROCESS": MitreMapping(tactic="Execution"),
    "HIGH_CPU": MitreMapping(tactic="Impact"),
    "HIGH_MEMORY": MitreMapping(tactic="Impact"),

    # File tampering / persistence / defense evasion
    "SENSITIVE_FILE_WRITE": MitreMapping(tactic="Defense Evasion"),
    "SENSITIVE_FILE_CREATE": MitreMapping(tactic="Persistence"),
    "SENSITIVE_FILE_DELETE": MitreMapping(tactic="Defense Evasion"),

    # Privilege escalation
    "ROOT_SHELL_SPAWN": MitreMapping(tactic="Privilege Escalation"),

    # Config audit findings
    "WEAK_SSH_CONFIG": MitreMapping(tactic="Credential Access"),
    "WORLD_WRITABLE_PATH": MitreMapping(tactic="Defense Evasion"),
    "FIREWALL_DISABLED": MitreMapping(tactic="Defense Evasion"),

    # ML anomaly is generic; we map to Discovery by default
    "ML_ANOMALY": MitreMapping(tactic="Discovery"),
}


def map_rule_to_mitre(rule_id: str) -> MitreMapping | None:
    return MITRE_MAP.get(rule_id)


__all__ = ["MitreMapping", "MITRE_MAP", "map_rule_to_mitre"]

