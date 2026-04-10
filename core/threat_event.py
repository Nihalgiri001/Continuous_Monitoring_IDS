"""
core/threat_event.py — ThreatEvent Dataclass

The canonical data structure passed through the event pipeline.
Every detection module (rules engine, ML, scanner) produces ThreatEvents.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from core.severity import Severity, get_severity


@dataclass
class ThreatEvent:
    rule_id: str
    description: str
    raw_data: dict = field(default_factory=dict)

    # Auto-populated
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    severity: Severity = field(init=False)
    source: str = "rules_engine"   # rules_engine | ml_engine | scanner | threat_intel
    resolved: bool = False

    def __post_init__(self):
        self.severity = get_severity(self.rule_id)

    @property
    def timestamp_iso(self) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["timestamp_iso"] = self.timestamp_iso
        return d

    def __repr__(self):
        return (
            f"ThreatEvent(rule={self.rule_id!r}, severity={self.severity.value}, "
            f"ts={self.timestamp_iso}, desc={self.description!r})"
        )


@dataclass
class SystemSnapshot:
    """Point-in-time view of system state, produced by the monitoring agent."""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    num_processes: int = 0
    processes: list[dict] = field(default_factory=list)           # top processes
    connections: list[dict] = field(default_factory=list)         # network conns
    listening_ports: list[int] = field(default_factory=list)
    num_new_connections: int = 0
    file_events: list[dict] = field(default_factory=list)         # from watchdog
    log_entries: list[str] = field(default_factory=list)

    def to_feature_vector(self) -> list[float]:
        """Compact numeric representation for the ML engine."""
        return [
            self.cpu_percent,
            self.memory_percent,
            float(self.num_processes),
            float(len(self.connections)),
            float(len(self.listening_ports)),
            float(self.num_new_connections),
            float(len(self.file_events)),
        ]


__all__ = ["ThreatEvent", "SystemSnapshot"]
