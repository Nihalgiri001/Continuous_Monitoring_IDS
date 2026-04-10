"""
agent/monitor.py — System Monitoring Agent

Continuously collects real-time snapshots of:
  - CPU & memory usage
  - Running processes (top consumers)
  - Network connections
  - Listening ports

Each snapshot is a SystemSnapshot pushed onto the central event_queue.
"""

import time
import logging
import threading
from pathlib import Path

import psutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MONITORING_INTERVAL_SECONDS
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

logger = logging.getLogger(__name__)

_prev_connections: set = set()


def _collect_processes(top_n: int = 20) -> list[dict]:
    procs = []
    for p in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_percent", "status", "cmdline"]
    ):
        try:
            info = p.info
            info["cmdline"] = " ".join(info.get("cmdline") or [])[:200]
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # Return top-N by CPU, then memory
    procs.sort(key=lambda x: (x.get("cpu_percent") or 0), reverse=True)
    return procs[:top_n]


def _collect_connections() -> tuple[list[dict], list[int], int]:
    """Returns (connections_list, listening_ports, num_new_connections)."""
    global _prev_connections
    conns = []
    listening = []
    current_keys: set = set()

    try:
        for c in psutil.net_connections(kind="inet"):
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else ""
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else ""
            key = (laddr, raddr, c.status)
            current_keys.add(key)

            entry = {
                "laddr": laddr,
                "raddr": raddr,
                "status": c.status,
                "pid": c.pid,
                "family": str(c.family),
            }
            conns.append(entry)

            if c.status == "LISTEN" and c.laddr:
                listening.append(c.laddr.port)

    except (psutil.AccessDenied, PermissionError):
        logger.debug("Access denied for net_connections — try running with sudo")

    new_count = len(current_keys - _prev_connections)
    _prev_connections = current_keys
    return conns, sorted(set(listening)), new_count


def collect_snapshot() -> SystemSnapshot:
    """Build a complete system snapshot synchronously."""
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    procs = _collect_processes()
    conns, listening, new_conns = _collect_connections()

    return SystemSnapshot(
        cpu_percent=cpu,
        memory_percent=mem.percent,
        memory_available_mb=mem.available / (1024 * 1024),
        num_processes=len(psutil.pids()),
        processes=procs,
        connections=conns,
        listening_ports=listening,
        num_new_connections=new_conns,
    )


class MonitoringAgent(threading.Thread):
    """Background thread that periodically collects snapshots and enqueues them."""

    daemon = True

    def __init__(self, interval: int = MONITORING_INTERVAL_SECONDS):
        super().__init__(name="MonitoringAgent")
        self.interval = interval
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("MonitoringAgent started (interval=%ds)", self.interval)
        # Warm-up: first cpu_percent call always returns 0.0
        psutil.cpu_percent(interval=None)
        time.sleep(1)

        while not self._stop_event.is_set():
            try:
                snapshot = collect_snapshot()
                safe_put(event_queue, snapshot)
                logger.debug(
                    "Snapshot: CPU=%.1f%% MEM=%.1f%% PROCS=%d CONNS=%d",
                    snapshot.cpu_percent,
                    snapshot.memory_percent,
                    snapshot.num_processes,
                    len(snapshot.connections),
                )
            except Exception as exc:
                logger.error("MonitoringAgent error: %s", exc, exc_info=True)

            self._stop_event.wait(self.interval)

        logger.info("MonitoringAgent stopped")


__all__ = ["MonitoringAgent", "collect_snapshot"]
