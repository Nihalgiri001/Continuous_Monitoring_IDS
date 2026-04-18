"""
alerts/alert_manager.py — Alert & Response System

Consumes ThreatEvents from threat_queue + vuln_queue.
Features:
  - Severity-based routing
  - Cooldown / rate limiting (prevents duplicate alert spam)
  - DB persistence
  - Pluggable notifier chain
"""

import logging
import threading
import time
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ALERT_COOLDOWN_SECONDS
from core.event_queue import threat_queue, vuln_queue, safe_get
from core.threat_event import ThreatEvent
from core.severity import Severity
from core.risk_scoring import RiskScoringEngine
from core.mitre_mapping import map_rule_to_mitre
from alerts.response.auto_response import AutonomousResponseEngine

logger = logging.getLogger(__name__)


class AlertManager(threading.Thread):
    """
    Drains both threat_queue and vuln_queue.
    Applies cooldown rate limiting, then dispatches to all registered notifiers.
    """

    daemon = True

    def __init__(self, db=None, notifiers: list | None = None):
        super().__init__(name="AlertManager")
        self._db = db
        self._notifiers = notifiers or []
        self._stop_event = threading.Event()
        self._risk = RiskScoringEngine()
        self._auto = AutonomousResponseEngine()

        # Cooldown tracker: rule_id+key → last_alert_timestamp
        # key is derived from the alert (e.g. IP, process name, port)
        self._last_alert: dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    # ── Cooldown / Rate Limiting ───────────────────────────────────────────────

    def _cooldown_key(self, event: ThreatEvent) -> str:
        """
        Unique identifier for deduplication.
        Combines rule_id with a distinguishing raw_data field if available.
        """
        rd = event.raw_data or {}
        discriminator = (
            rd.get("pid") or rd.get("raddr") or rd.get("port") or
            rd.get("src") or rd.get("name") or ""
        )
        return f"{event.rule_id}::{discriminator}"

    def _is_rate_limited(self, event: ThreatEvent) -> bool:
        key = self._cooldown_key(event)
        now = time.time()
        with self._lock:
            last = self._last_alert[key]
            if now - last < ALERT_COOLDOWN_SECONDS:
                logger.debug(
                    "Rate-limited: %s (%.0fs ago)", key, now - last
                )
                return True
            self._last_alert[key] = now
            return False

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, event: ThreatEvent):
        # Enrich with risk score + MITRE mapping + optional auto-response actions.
        try:
            rs = self._risk.score(event)
            event.risk_score = rs.score
            event.risk_label = rs.label
            event.computed_severity = rs.label  # use risk-derived label for UI/DB
            # Preserve breakdown for explainability / audits
            event.raw_data = event.raw_data or {}
            event.raw_data["risk_breakdown"] = rs.breakdown
        except Exception as e:
            logger.debug("Risk scoring failed: %s", e)

        try:
            mm = map_rule_to_mitre(event.rule_id)
            if mm:
                event.mitre_tactic = mm.tactic
                event.mitre_technique = mm.technique
        except Exception:
            pass

        try:
            if event.risk_score is not None:
                action_str = self._auto.respond(event, int(event.risk_score))
                if action_str:
                    event.auto_action_taken = action_str
        except Exception as e:
            logger.debug("Auto-response failed: %s", e)

        if self._db:
            try:
                self._db.insert_threat(event)
            except Exception as e:
                logger.error("DB insert failed: %s", e)

        for notifier in self._notifiers:
            try:
                notifier.send(event)
                if self._db:
                    self._db.log_alert(event.id, notifier.__class__.__name__, "sent")
            except Exception as e:
                logger.error("Notifier %s failed: %s", notifier.__class__.__name__, e)
                if self._db:
                    self._db.log_alert(event.id, notifier.__class__.__name__, f"error: {e}")

    def add_notifier(self, notifier):
        self._notifiers.append(notifier)

    # ── Thread loop ───────────────────────────────────────────────────────────

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info(
            "AlertManager started (%d notifiers, cooldown=%ds)",
            len(self._notifiers),
            ALERT_COOLDOWN_SECONDS,
        )
        while not self._stop_event.is_set():
            # Check both queues each tick
            processed = False
            for q in (threat_queue, vuln_queue):
                event = safe_get(q, timeout=0.5)
                if event is None:
                    continue
                if not isinstance(event, ThreatEvent):
                    continue
                if self._is_rate_limited(event):
                    continue
                self._dispatch(event)
                processed = True

            if not processed:
                time.sleep(0.1)

        logger.info("AlertManager stopped")


__all__ = ["AlertManager"]
