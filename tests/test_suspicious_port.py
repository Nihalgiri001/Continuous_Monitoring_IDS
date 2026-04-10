"""tests/test_suspicious_port.py — Simulate SUSPICIOUS_PORT + BLACKLISTED_IP detection."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.threat_event import SystemSnapshot, ThreatEvent
from core.event_queue import event_queue, threat_queue, safe_put, safe_get
from detection.rules_engine import RulesEngine
from threat_intel.intel_manager import IntelManager

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def _drain_queues():
    """Drain both shared queues between tests to prevent cross-test pollution."""
    for q in (event_queue, threat_queue):
        while not q.empty():
            try:
                q.get_nowait()
            except Exception:
                break


def test_suspicious_port():
    _drain_queues()
    print("\n── Test: SUSPICIOUS_PORT Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=40.0,
        processes=[],
        connections=[
            {"laddr": "192.168.1.10:52341", "raddr": "203.0.113.99:4444",
             "status": "ESTABLISHED", "pid": 1234},
        ],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    time.sleep(1.0)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "SUSPICIOUS_PORT":
            print(f"  {PASS} SUSPICIOUS_PORT fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} SUSPICIOUS_PORT rule did not fire")
    engine.stop()
    engine.join(timeout=2)
    _drain_queues()
    return found


def test_blacklisted_ip():
    _drain_queues()
    print("\n── Test: BLACKLISTED_IP Rule ──")
    intel = IntelManager()
    # Manually inject a test IP into the blacklist
    with intel._lock:
        intel._bad_ips.add("10.20.30.40")

    engine = RulesEngine(intel_manager=intel)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=40.0,
        processes=[],
        connections=[
            {"laddr": "192.168.1.10:54321", "raddr": "10.20.30.40:443",
             "status": "ESTABLISHED", "pid": 5678},
        ],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    time.sleep(1.0)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "BLACKLISTED_IP":
            print(f"  {PASS} BLACKLISTED_IP fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} BLACKLISTED_IP rule did not fire")

    engine.stop()
    engine.join(timeout=2)
    intel.stop()
    _drain_queues()
    return found


def test_rapid_connections():
    _drain_queues()
    print("\n── Test: RAPID_CONNECTIONS Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=40.0,
        processes=[],
        connections=[],
        listening_ports=[],
        num_new_connections=50,   # Above threshold of 30
    )
    safe_put(event_queue, snap)
    time.sleep(1.0)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "RAPID_CONNECTIONS":
            print(f"  {PASS} RAPID_CONNECTIONS fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} RAPID_CONNECTIONS rule did not fire")
    engine.stop()
    engine.join(timeout=2)
    _drain_queues()
    return found


if __name__ == "__main__":
    r1 = test_suspicious_port()
    r2 = test_blacklisted_ip()
    r3 = test_rapid_connections()
    total = sum([r1, r2, r3])
    print(f"\nResults: {total}/3 passed")
