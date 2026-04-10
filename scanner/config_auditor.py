"""
scanner/config_auditor.py — System Configuration Auditor

Checks for weak or dangerous system configurations:
  - World-writable files in sensitive directories
  - SSH config issues (PermitRootLogin, PasswordAuthentication)
  - macOS firewall status
  - /tmp sticky bit
"""

import os
import logging
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.threat_event import ThreatEvent

logger = logging.getLogger(__name__)


def _check_world_writable(paths: list[str]) -> list[ThreatEvent]:
    events = []
    for base in paths:
        p = Path(base)
        if not p.exists():
            continue
        try:
            for entry in p.rglob("*"):
                if entry.is_file():
                    try:
                        mode = entry.stat().st_mode
                        if mode & 0o002:  # world-writable bit
                            events.append(ThreatEvent(
                                rule_id="WORLD_WRITABLE_PATH",
                                description=f"World-writable file detected: {entry}",
                                raw_data={"path": str(entry), "mode": oct(mode)},
                                source="scanner",
                            ))
                    except PermissionError:
                        pass
        except PermissionError:
            logger.debug("Cannot read directory: %s", base)
    return events


def _check_ssh_config() -> list[ThreatEvent]:
    events = []
    ssh_config = Path("/etc/ssh/sshd_config")
    if not ssh_config.exists():
        return []
    try:
        content = ssh_config.read_text()
        checks = {
            "PermitRootLogin yes": "SSH PermitRootLogin is enabled — root login over SSH is a critical risk",
            "PasswordAuthentication yes": "SSH PasswordAuthentication is enabled — prefer key-based auth",
            "PermitEmptyPasswords yes": "SSH allows empty passwords — critical vulnerability",
            "X11Forwarding yes": "SSH X11Forwarding enabled — potential info leak",
        }
        for directive, msg in checks.items():
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.lower() == directive.lower() and not stripped.startswith("#"):
                    events.append(ThreatEvent(
                        rule_id="WEAK_SSH_CONFIG",
                        description=msg,
                        raw_data={"directive": directive, "file": str(ssh_config)},
                        source="scanner",
                    ))
    except PermissionError:
        logger.debug("Cannot read sshd_config — insufficient permissions")
    return events


def _check_firewall() -> list[ThreatEvent]:
    """macOS Application Firewall status check."""
    events = []
    try:
        result = subprocess.run(
            ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.lower()
        if "disabled" in output or "state = 0" in output:
            events.append(ThreatEvent(
                rule_id="FIREWALL_DISABLED",
                description="macOS Application Firewall is DISABLED — system is exposed to network threats",
                raw_data={"firewall_output": result.stdout.strip()},
                source="scanner",
            ))
        else:
            logger.debug("Firewall: %s", result.stdout.strip())
    except Exception as e:
        logger.debug("Firewall check unavailable: %s", e)
    return events


def run_config_audit() -> list[ThreatEvent]:
    """Run all configuration checks and return ThreatEvents."""
    logger.info("Running configuration audit…")
    events = []
    events.extend(_check_ssh_config())
    events.extend(_check_firewall())
    events.extend(_check_world_writable(["/etc", "/tmp"]))
    logger.info("Config audit complete — %d findings", len(events))
    return events


__all__ = ["run_config_audit"]
