"""
core/event_queue.py — Central Event Pipeline

A shared queue.Queue instance that decouples producers (monitoring agent,
scanner, threat intel) from consumers (detection engine, alert manager).

Usage:
    from core.event_queue import event_queue
    event_queue.put(snapshot)          # producer
    item = event_queue.get(timeout=1)  # consumer
"""

from queue import Queue, Empty
import logging

logger = logging.getLogger(__name__)

# ── Singleton queues ──────────────────────────────────────────────────────────

# Raw system snapshots: agent → detection engine
event_queue: Queue = Queue(maxsize=512)

# Threat events: detection engine / scanner → alert manager → dashboard
threat_queue: Queue = Queue(maxsize=256)

# Vulnerability results: scanner → dashboard / db
vuln_queue: Queue = Queue(maxsize=128)


def safe_put(q: Queue, item, block: bool = False) -> bool:
    """Non-blocking put that drops items when queue is full (back-pressure)."""
    try:
        q.put(item, block=block)
        return True
    except Exception:
        logger.warning("Queue full — dropped one item (back-pressure)")
        return False


def safe_get(q: Queue, timeout: float = 1.0):
    """Get with timeout. Returns None on timeout rather than raising."""
    try:
        return q.get(timeout=timeout)
    except Empty:
        return None


__all__ = ["event_queue", "threat_queue", "vuln_queue", "safe_put", "safe_get"]
