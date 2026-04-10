"""
scanner/port_scanner.py — Vulnerability Port Scanner

Scans localhost for open ports, maps them to known risk descriptions,
and stores results via the database layer.

Uses python-nmap if available; falls back to a pure socket scanner.
"""

import logging
import socket
import threading
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SCAN_TARGET, SCAN_INTERVAL_SECONDS, NMAP_TIMEOUT_SECONDS,
    NMAP_ARGS, RISKY_PORTS
)
from core.event_queue import vuln_queue, safe_put
from core.threat_event import ThreatEvent
from core.severity import Severity

logger = logging.getLogger(__name__)


def _nmap_scan(target: str) -> list[dict]:
    """Attempt nmap scan. Returns list of port-result dicts."""
    try:
        import nmap
        nm = nmap.PortScanner()
        nm.scan(hosts=target, arguments=NMAP_ARGS, timeout=NMAP_TIMEOUT_SECONDS)
        results = []
        for host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                for port, info in nm[host][proto].items():
                    if info["state"] == "open":
                        results.append({
                            "port": port,
                            "protocol": proto,
                            "service": info.get("name", "unknown"),
                            "version": info.get("version", ""),
                            "scanner": "nmap",
                        })
        logger.info("nmap found %d open ports", len(results))
        return results
    except ImportError:
        logger.warning("python-nmap not installed — falling back to socket scanner")
        return []
    except Exception as e:
        logger.warning("nmap scan failed (%s) — falling back to socket scanner", e)
        return []


def _socket_scan(target: str, ports: list[int] | None = None) -> list[dict]:
    """Pure-socket fallback scanner. Checks well-known + risky ports."""
    if ports is None:
        ports = sorted(set(list(RISKY_PORTS.keys()) + list(range(1, 1025))))

    results = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((target, port)) == 0:
                    # Try to grab service name
                    try:
                        service = socket.getservbyport(port)
                    except OSError:
                        service = "unknown"
                    results.append({
                        "port": port,
                        "protocol": "tcp",
                        "service": service,
                        "version": "",
                        "scanner": "socket",
                    })
        except Exception:
            pass
    logger.info("socket scanner found %d open ports", len(results))
    return results


def _classify_port(port_info: dict) -> tuple[str, str]:
    """
    Returns (severity_str, risk_description) for a given open port.
    Uses the RISKY_PORTS map from config.
    """
    port = port_info["port"]
    if port in RISKY_PORTS:
        risk_desc = RISKY_PORTS[port]
        # Escalate severity for the most dangerous ports
        critical_ports = {4444, 31337, 23, 512, 513, 514}
        high_ports = {21, 445, 3389, 6379, 27017, 5900, 9200}
        if port in critical_ports:
            severity = "Critical"
        elif port in high_ports:
            severity = "High"
        else:
            severity = "Medium"
        return severity, risk_desc
    else:
        return "Low", f"Port {port}/{port_info['protocol']} ({port_info['service']}) is open"


def run_scan(target: str = SCAN_TARGET) -> list[dict]:
    """Run a full scan and return enriched results."""
    logger.info("Starting port scan on %s…", target)
    raw = _nmap_scan(target) or _socket_scan(target)
    enriched = []
    for r in raw:
        severity, desc = _classify_port(r)
        r["severity"] = severity
        r["risk_description"] = desc
        enriched.append(r)
        logger.info(
            "[SCAN] Port %d/%s (%s) — %s [%s]",
            r["port"], r["protocol"], r["service"], desc, severity
        )
    return enriched


class PortScanner(threading.Thread):
    """Runs periodic port scans, emits results to vuln_queue and DB."""

    daemon = True

    def __init__(self, db=None, interval: int = SCAN_INTERVAL_SECONDS):
        super().__init__(name="PortScanner")
        self._db = db
        self.interval = interval
        self._stop_event = threading.Event()
        self.last_results: list[dict] = []

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("PortScanner started (interval=%ds)", self.interval)
        while not self._stop_event.is_set():
            try:
                results = run_scan()
                self.last_results = results
                for r in results:
                    # Emit as ThreatEvent for high/critical findings
                    rule = "OPEN_RISKY_PORT" if r["severity"] in ("High", "Critical", "Medium") else "OPEN_PORT"
                    evt = ThreatEvent(
                        rule_id=rule,
                        description=r["risk_description"],
                        raw_data=r,
                        source="scanner",
                    )
                    safe_put(vuln_queue, evt)

                    if self._db:
                        self._db.insert_vulnerability(
                            scanner=r["scanner"],
                            port=r["port"],
                            service=r["service"],
                            severity=r["severity"],
                            detail=r["risk_description"],
                        )
            except Exception as exc:
                logger.error("PortScanner error: %s", exc, exc_info=True)

            self._stop_event.wait(self.interval)

        logger.info("PortScanner stopped")


__all__ = ["PortScanner", "run_scan"]
