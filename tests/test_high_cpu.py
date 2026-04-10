"""tests/test_high_cpu.py — Simulate HIGH_CPU and HIGH_MEMORY detection."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.threat_event import SystemSnapshot, ThreatEvent
from core.event_queue import event_queue, threat_queue, safe_put, safe_get
from detection.rules_engine import RulesEngine

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def test_high_cpu():
    print("\n── Test: HIGH_CPU Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    # Inject a snapshot with a CPU-hogging process
    snap = SystemSnapshot(
        cpu_percent=45.0,
        memory_percent=55.0,
        processes=[
            {"pid": 9999, "name": "stress-test", "cpu_percent": 95.5,
             "memory_percent": 2.0, "username": "user", "cmdline": "stress --cpu 4"},
        ],
        connections=[],
        listening_ports=[],
        num_new_connections=0,
    )
    safe_put(event_queue, snap)
    time.sleep(0.5)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "HIGH_CPU":
            print(f"  {PASS} HIGH_CPU fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} HIGH_CPU rule did not fire (threshold not met?)")

    engine.stop()
    return found


def test_high_memory():
    print("\n── Test: HIGH_MEMORY Rule ──")
    engine = RulesEngine(intel_manager=None)
    engine.start()

    snap = SystemSnapshot(
        cpu_percent=10.0,
        memory_percent=92.3,
        memory_available_mb=512.0,
        processes=[],
        connections=[],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    time.sleep(0.5)

    found = False
    while True:
        evt = safe_get(threat_queue, timeout=1.0)
        if evt is None:
            break
        if isinstance(evt, ThreatEvent) and evt.rule_id == "HIGH_MEMORY":
            print(f"  {PASS} HIGH_MEMORY fired — severity={evt.severity.value}")
            print(f"         desc: {evt.description}")
            found = True
            break

    if not found:
        print(f"  {FAIL} HIGH_MEMORY rule did not fire")

    engine.stop()
    return found


if __name__ == "__main__":
    r1 = test_high_cpu()
    r2 = test_high_memory()
    print(f"\nResults: {'ALL PASSED' if r1 and r2 else 'SOME FAILED'}")
