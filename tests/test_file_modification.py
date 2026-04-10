"""tests/test_file_modification.py — Simulate SENSITIVE_FILE_WRITE / DELETE detection."""

import sys, time, tempfile, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.threat_event import SystemSnapshot, ThreatEvent
from core.event_queue import event_queue, threat_queue, safe_put, safe_get
from detection.rules_engine import RulesEngine

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def test_sensitive_file_write():
    print("\n── Test: SENSITIVE_FILE_WRITE / CREATE Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=30.0,
        processes=[],
        connections=[],
        listening_ports=[],
        file_events=[
            {"type": "modify", "src": "/etc/hosts", "dest": ""},
            {"type": "create", "src": "/bin/new_binary", "dest": ""},
        ],
    )
    safe_put(event_queue, snap)
    time.sleep(0.5)

    found_write  = False
    found_create = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent):
            if evt.rule_id == "SENSITIVE_FILE_WRITE":
                print(f"  {PASS} SENSITIVE_FILE_WRITE fired — {evt.description}")
                found_write = True
            elif evt.rule_id == "SENSITIVE_FILE_CREATE":
                print(f"  {PASS} SENSITIVE_FILE_CREATE fired — {evt.description}")
                found_create = True

    if not found_write:
        print(f"  {FAIL} SENSITIVE_FILE_WRITE did not fire")
    if not found_create:
        print(f"  {FAIL} SENSITIVE_FILE_CREATE did not fire")

    engine.stop()
    return found_write and found_create


def test_sensitive_file_delete():
    print("\n── Test: SENSITIVE_FILE_DELETE Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=30.0,
        processes=[],
        connections=[],
        listening_ports=[],
        file_events=[
            {"type": "delete", "src": "/etc/passwd", "dest": ""},
        ],
    )
    safe_put(event_queue, snap)
    time.sleep(0.5)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "SENSITIVE_FILE_DELETE":
            print(f"  {PASS} SENSITIVE_FILE_DELETE fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} SENSITIVE_FILE_DELETE did not fire")

    engine.stop()
    return found


def test_severity_scoring():
    """Verify the severity scoring system returns correct values."""
    print("\n── Test: Severity Scoring System ──")
    from core.severity import get_severity, Severity, SEVERITY_MAP

    all_pass = True
    checks = [
        ("HIGH_CPU",         Severity.MEDIUM),
        ("BLACKLISTED_IP",   Severity.HIGH),
        ("ROOT_SHELL_SPAWN", Severity.CRITICAL),
        ("ML_ANOMALY",       Severity.ANOMALY),
        ("SENSITIVE_FILE_DELETE", Severity.CRITICAL),
        ("OPEN_RISKY_PORT",  Severity.HIGH),
    ]
    for rule_id, expected in checks:
        got = get_severity(rule_id)
        ok = got == expected
        icon = PASS if ok else FAIL
        print(f"  {icon} {rule_id}: expected={expected.value} got={got.value}")
        if not ok:
            all_pass = False

    return all_pass


def test_alert_cooldown():
    """Verify the rate-limiting / cooldown mechanism."""
    print("\n── Test: Alert Cooldown / Rate Limiting ──")
    from alerts.alert_manager import AlertManager
    from core.threat_event import ThreatEvent

    received = []

    class _CountNotifier:
        def send(self, event):
            received.append(event)

    mgr = AlertManager(db=None, notifiers=[_CountNotifier()])

    # Build identical events
    evt = ThreatEvent(rule_id="HIGH_CPU", description="Test", raw_data={"pid": 42})

    # Dispatch 5 times — only first should go through (cooldown=60s)
    for _ in range(5):
        if not mgr._is_rate_limited(evt):
            mgr._dispatch(evt)
        else:
            pass  # rate limited

    ok = len(received) == 1
    icon = PASS if ok else FAIL
    print(f"  {icon} Cooldown: sent 5, delivered {len(received)} (expected 1)")
    return ok


if __name__ == "__main__":
    r1 = test_sensitive_file_write()
    r2 = test_sensitive_file_delete()
    r3 = test_severity_scoring()
    r4 = test_alert_cooldown()
    total = sum([r1, r2, r3, r4])
    print(f"\nResults: {total}/4 passed")
