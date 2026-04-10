"""
alerts/notifiers/desktop.py — macOS Desktop Notification

Sends native macOS notifications for High/Critical alerts
via osascript (no external dependencies required).
Silently skips on non-macOS platforms.
"""

import logging
import platform
import subprocess

from core.threat_event import ThreatEvent
from core.severity import Severity
from config import ENABLE_DESKTOP_NOTIFICATIONS

logger = logging.getLogger(__name__)

_NOTIFY_SEVERITIES = {Severity.HIGH, Severity.CRITICAL, Severity.ANOMALY}


class DesktopNotifier:
    """Sends macOS native notifications for important alerts."""

    def send(self, event: ThreatEvent):
        if not ENABLE_DESKTOP_NOTIFICATIONS:
            return
        if event.severity not in _NOTIFY_SEVERITIES:
            return
        if platform.system() != "Darwin":
            return

        title = f"🚨 CyberCBP — {event.severity.value.upper()}"
        body  = f"{event.rule_id}: {event.description[:150]}"

        try:
            script = (
                f'display notification "{body}" '
                f'with title "{title}" '
                f'sound name "Basso"'
            )
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            logger.debug("Desktop notification sent: %s", event.rule_id)
        except Exception as e:
            logger.warning("Desktop notification failed: %s", e)


__all__ = ["DesktopNotifier"]
