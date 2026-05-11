"""
alerts/notifiers/desktop.py — macOS Desktop Notification

Sends native macOS notifications for Medium/High/Critical/Anomaly alerts
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

_NOTIFY_SEVERITIES = {
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
    Severity.ANOMALY,
}


def _escape_applescript(text: str) -> str:
    """Escape strings embedded into an AppleScript literal."""
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')


class DesktopNotifier:
    """Sends macOS native notifications for important alerts."""

    def send(self, event: ThreatEvent):
        if not ENABLE_DESKTOP_NOTIFICATIONS:
            return
        if event.severity not in _NOTIFY_SEVERITIES:
            return
        if platform.system() != "Darwin":
            return

        title = _escape_applescript(f"CyberCBP — {event.severity.value.upper()}")
        body = _escape_applescript(f"{event.rule_id}: {event.description[:150]}")

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
