"""
alerts/notifiers/console.py — Rich Console Notifier

Prints color-coded, emoji-enriched threat alerts to the terminal.
Uses the `rich` library for styled output.
"""

import logging
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from core.threat_event import ThreatEvent
from core.severity import Severity

logger = logging.getLogger(__name__)
_console = Console(stderr=False)

_SEVERITY_STYLE = {
    Severity.LOW:      "bold green",
    Severity.MEDIUM:   "bold yellow",
    Severity.HIGH:     "bold red",
    Severity.CRITICAL: "bold white on red",
    Severity.ANOMALY:  "bold magenta",
}


class ConsoleNotifier:
    """Sends rich, styled threat alerts to stdout."""

    def send(self, event: ThreatEvent):
        sev = event.severity
        style = _SEVERITY_STYLE.get(sev, "white")
        emoji = sev.emoji

        ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")

        # Build content
        content = Text()
        content.append(f"{emoji}  [{sev.value.upper()}]  ", style=style)
        content.append(f"{event.rule_id}\n", style="bold white")
        content.append(f"   {event.description}\n", style="white")
        content.append(f"   Source: {event.source}  •  {ts}", style="dim")

        border_style = "red" if sev in (Severity.HIGH, Severity.CRITICAL) else "yellow"
        _console.print(Panel(content, border_style=border_style, expand=False))


__all__ = ["ConsoleNotifier"]
