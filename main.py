"""
main.py — CyberCBP Orchestrator

Bootstraps and wires all modules together, then runs until SIGINT/SIGTERM.

Pipeline:
  MonitoringAgent  →  event_queue  →  RulesEngine  → threat_queue → AlertManager
                   ↘  event_queue  →  AnomalyDetector ↗
  FileWatcher      →  (drained by MonitoringAgent, attached to snapshots)
  PortScanner      →  vuln_queue   → AlertManager
  IntelManager     →  (queried by RulesEngine)
  AlertManager     →  DB + ConsoleNotifier + DesktopNotifier + SSE push
  Dashboard Flask  ←  DB / live SSE
"""

import logging
import signal
import sys
import threading
import time
from pathlib import Path

# ── Logging setup (before any imports that log) ───────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cybercbp.log", mode="a"),
    ],
)
logger = logging.getLogger("main")

# ── Module imports ────────────────────────────────────────────────────────────
from config import MONITORING_INTERVAL_SECONDS, SCAN_INTERVAL_SECONDS
from db.database import db

from core.event_queue import event_queue, threat_queue
from core.threat_event import SystemSnapshot

from agent.monitor import MonitoringAgent, collect_snapshot
from agent.file_watcher import FileWatcher

from detection.rules_engine import RulesEngine

from ml_engine.trainer import ModelTrainer
from ml_engine.detector import AnomalyDetector

from threat_intel.intel_manager import IntelManager

from scanner.port_scanner import PortScanner
from scanner.config_auditor import run_config_audit

from alerts.alert_manager import AlertManager
from alerts.notifiers.console import ConsoleNotifier
from alerts.notifiers.desktop import DesktopNotifier

from reports.exporter import ReportExporter

import dashboard.app as dash_app

# ── Stop flag ─────────────────────────────────────────────────────────────────
_stop_event = threading.Event()


def _handle_signal(sig, frame):
    logger.info("Shutdown signal received (%s) — stopping…", sig)
    _stop_event.set()


# ── Snapshot enricher (attaches file events to snapshots) ─────────────────────
class EnrichedMonitor(threading.Thread):
    """
    Wraps MonitoringAgent to also drain FileWatcher events and inject
    them into each snapshot before putting it on event_queue.
    """
    daemon = True

    def __init__(self, file_watcher: FileWatcher):
        super().__init__(name="EnrichedMonitor")
        self._fw = file_watcher
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        logger.info("EnrichedMonitor started")
        psutil_warmup = True
        import psutil
        psutil.cpu_percent(interval=None)
        time.sleep(1)

        while not self._stop.is_set():
            try:
                snap = collect_snapshot()
                snap.file_events = self._fw.drain()

                # Make the latest snapshot available to the dashboard
                dash_app.update_snapshot(snap)

                from core.event_queue import safe_put
                safe_put(event_queue, snap)

            except Exception as e:
                logger.error("EnrichedMonitor error: %s", e)

            self._stop.wait(MONITORING_INTERVAL_SECONDS)

        logger.info("EnrichedMonitor stopped")


# ── SSE-forwarding alert wrapper ──────────────────────────────────────────────
class SSEForwardingNotifier:
    """Forwards every dispatched ThreatEvent to the SSE broadcast."""
    def send(self, event):
        try:
            dash_app.push_event_to_sse(event.to_dict())
        except Exception as e:
            logger.debug("SSE forward failed: %s", e)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("  CyberCBP — Proactive Threat Detection System")
    logger.info("=" * 60)

    # ── Signal handlers ───────────────────────────────────────────────────────
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # ── Initialise modules ────────────────────────────────────────────────────
    logger.info("[1/8] Starting Threat Intelligence…")
    intel = IntelManager()
    intel.start()

    logger.info("[2/8] Starting File Watcher…")
    file_watcher = FileWatcher()
    file_watcher.start()

    logger.info("[3/8] Starting Monitoring Agent…")
    monitor = EnrichedMonitor(file_watcher)
    monitor.start()

    logger.info("[4/8] Starting Rule-Based Detection Engine…")
    rules_engine = RulesEngine(intel_manager=intel)
    rules_engine.start()

    logger.info("[5/8] Starting ML Trainer + Anomaly Detector…")
    trainer  = ModelTrainer()
    detector = AnomalyDetector(trainer)
    trainer.start()
    #detector.start()

    logger.info("[6/8] Starting Alert Manager…")
    exporter = ReportExporter(db)
    alert_mgr = AlertManager(
        db=db,
        notifiers=[
            ConsoleNotifier(),
            DesktopNotifier(),
            SSEForwardingNotifier(),
        ],
    )
    alert_mgr.start()

    logger.info("[7/8] Starting Vulnerability Scanner…")
    port_scanner = PortScanner(db=db, interval=SCAN_INTERVAL_SECONDS)
    port_scanner.start()

    # Run initial config audit in background
    def _initial_audit():
        time.sleep(5)
        events = run_config_audit()
        for e in events:
            db.insert_threat(e)
            from core.event_queue import safe_put
            safe_put(threat_queue, e)
        logger.info("Initial config audit complete — %d findings", len(events))

    threading.Thread(target=_initial_audit, daemon=True, name="InitAudit").start()

    logger.info("[8/8] Starting Dashboard…")
    dash_app.init_app(
        db=db,
        intel=intel,
        port_scanner=port_scanner,
        exporter=exporter,
    )
    dashboard_thread = threading.Thread(
        target=dash_app.run_dashboard, daemon=True, name="Dashboard"
    )
    dashboard_thread.start()

    logger.info("✅ All modules running. Dashboard → http://127.0.0.1:5000")
    logger.info("   Press Ctrl+C to stop.\n")

    # ── Main loop ─────────────────────────────────────────────────────────────
    while not _stop_event.is_set():
        _stop_event.wait(1)

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    logger.info("Shutting down all modules…")
    for module in [monitor, file_watcher, rules_engine, detector, trainer,
                   alert_mgr, port_scanner, intel]:
        try:
            module.stop()
        except Exception:
            pass

    logger.info("CyberCBP stopped cleanly. Goodbye.")
    sys.exit(0)


if __name__ == "__main__":
    main()
