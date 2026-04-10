"""
detection/rules_engine.py — Rule-Based Intrusion Detection System

Consumes SystemSnapshot objects from the event_queue, evaluates each
registered rule, and emits ThreatEvent objects onto the threat_queue.

Rules are functions that take a SystemSnapshot and threat_intel IntelManager
and return a list of ThreatEvent objects (empty = no threat detected).
"""

import logging
import threading
from pathlib import Path
from typing import Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CPU_ALERT_THRESHOLD,
    MEMORY_ALERT_THRESHOLD,
    RAPID_CONNECTION_THRESHOLD,
    SUSPICIOUS_PORTS,
)
from core.event_queue import event_queue, threat_queue, safe_put, safe_get
from core.threat_event import ThreatEvent, SystemSnapshot

logger = logging.getLogger(__name__)

# Type alias
RuleFn = Callable[[SystemSnapshot, object], list[ThreatEvent]]

# ── Built-in Rules ─────────────────────────────────────────────────────────────

def rule_high_cpu(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    events = []
    for proc in snap.processes:
        cpu = proc.get("cpu_percent") or 0
        if cpu >= CPU_ALERT_THRESHOLD:
            events.append(ThreatEvent(
                rule_id="HIGH_CPU",
                description=(
                    f"Process '{proc.get('name')}' (PID {proc.get('pid')}) "
                    f"is using {cpu:.1f}% CPU"
                ),
                raw_data=proc,
                source="rules_engine",
            ))
    return events


def rule_high_memory(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    if snap.memory_percent >= MEMORY_ALERT_THRESHOLD:
        return [ThreatEvent(
            rule_id="HIGH_MEMORY",
            description=f"System memory at {snap.memory_percent:.1f}% "
                        f"(only {snap.memory_available_mb:.0f} MB free)",
            raw_data={"memory_percent": snap.memory_percent,
                      "available_mb": snap.memory_available_mb},
            source="rules_engine",
        )]
    return []


def rule_blacklisted_process(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    events = []
    for proc in snap.processes:
        name = (proc.get("name") or "").lower()
        cmd  = (proc.get("cmdline") or "").lower()
        if intel and intel.is_suspicious_process(name):
            events.append(ThreatEvent(
                rule_id="BLACKLISTED_PROCESS",
                description=f"Blacklisted process detected: '{proc.get('name')}' "
                            f"(PID {proc.get('pid')})",
                raw_data=proc,
                source="rules_engine",
            ))
    return events


def rule_blacklisted_ip(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    if not intel:
        return []
    events = []
    seen = set()
    for conn in snap.connections:
        raddr = conn.get("raddr", "")
        if not raddr:
            continue
        ip = raddr.split(":")[0]
        if ip in seen:
            continue
        seen.add(ip)
        if intel.is_blacklisted_ip(ip):
            events.append(ThreatEvent(
                rule_id="BLACKLISTED_IP",
                description=f"Connection to blacklisted IP: {ip}",
                raw_data=conn,
                source="rules_engine",
            ))
    return events


def rule_suspicious_port(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    events = []
    seen_ports = set()
    for conn in snap.connections:
        raddr = conn.get("raddr", "")
        if not raddr:
            continue
        try:
            port = int(raddr.split(":")[-1])
        except ValueError:
            continue
        if port in SUSPICIOUS_PORTS and port not in seen_ports:
            seen_ports.add(port)
            events.append(ThreatEvent(
                rule_id="SUSPICIOUS_PORT",
                description=f"Outbound connection to suspicious port {port} "
                            f"(raddr: {raddr})",
                raw_data=conn,
                source="rules_engine",
            ))
    return events


def rule_rapid_connections(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    if snap.num_new_connections >= RAPID_CONNECTION_THRESHOLD:
        return [ThreatEvent(
            rule_id="RAPID_CONNECTIONS",
            description=f"Rapid connection burst: {snap.num_new_connections} new "
                        f"connections in one monitoring interval",
            raw_data={"new_connections": snap.num_new_connections},
            source="rules_engine",
        )]
    return []


def rule_sensitive_file_write(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    events = []
    sensitive_prefixes = ("/etc/", "/bin/", "/usr/bin/", "/usr/local/bin/")
    for fe in snap.file_events:
        src = fe.get("src", "")
        evt_type = fe.get("type", "")
        if evt_type in ("modify", "create") and any(
            src.startswith(p) for p in sensitive_prefixes
        ):
            rule = "SENSITIVE_FILE_WRITE" if evt_type == "modify" else "SENSITIVE_FILE_CREATE"
            events.append(ThreatEvent(
                rule_id=rule,
                description=f"Sensitive path {evt_type}d: {src}",
                raw_data=fe,
                source="rules_engine",
            ))
        elif evt_type == "delete" and any(
            src.startswith(p) for p in sensitive_prefixes
        ):
            events.append(ThreatEvent(
                rule_id="SENSITIVE_FILE_DELETE",
                description=f"File deleted from sensitive path: {src}",
                raw_data=fe,
                source="rules_engine",
            ))
    return events


def rule_root_shell_spawn(snap: SystemSnapshot, intel) -> list[ThreatEvent]:
    events = []
    shell_names = {"bash", "sh", "zsh", "fish", "dash"}
    for proc in snap.processes:
        name = (proc.get("name") or "").lower()
        user = (proc.get("username") or "").lower()
        if name in shell_names and user == "root":
            events.append(ThreatEvent(
                rule_id="ROOT_SHELL_SPAWN",
                description=f"Root shell spawned: '{proc.get('name')}' "
                            f"(PID {proc.get('pid')})",
                raw_data=proc,
                source="rules_engine",
            ))
    return events


# ── Registry ───────────────────────────────────────────────────────────────────

DEFAULT_RULES: list[RuleFn] = [
    rule_high_cpu,
    rule_high_memory,
    rule_blacklisted_process,
    rule_blacklisted_ip,
    rule_suspicious_port,
    rule_rapid_connections,
    rule_sensitive_file_write,
    rule_root_shell_spawn,
]


# ── Engine Thread ──────────────────────────────────────────────────────────────

class RulesEngine(threading.Thread):
    """
    Consumes snapshots from event_queue, runs all rules,
    and pushes ThreatEvents onto threat_queue.
    """
    daemon = True

    def __init__(self, intel_manager=None, extra_rules: list[RuleFn] | None = None):
        super().__init__(name="RulesEngine")
        self.intel = intel_manager
        self.rules: list[RuleFn] = DEFAULT_RULES + (extra_rules or [])
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("RulesEngine started with %d rules", len(self.rules))
        while not self._stop_event.is_set():
            snap = safe_get(event_queue, timeout=1.0)
            if snap is None:
                continue
            if not isinstance(snap, SystemSnapshot):
                continue
            for rule in self.rules:
                try:
                    events = rule(snap, self.intel)
                    for evt in events:
                        safe_put(threat_queue, evt)
                        logger.info("[THREAT] %s — %s", evt.rule_id, evt.description)
                except Exception as exc:
                    logger.error("Rule %s crashed: %s", rule.__name__, exc, exc_info=True)

        logger.info("RulesEngine stopped")


__all__ = ["RulesEngine", "DEFAULT_RULES"]
