"""
alerts/response/auto_block.py — Automatic IP Blocking (stub)

Blocks malicious IPs using macOS `pfctl`. Disabled by default —
must be explicitly enabled in config.py AND run with sudo privileges.
"""

import logging
import subprocess
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import ENABLE_AUTO_BLOCK_IPS

logger = logging.getLogger(__name__)

_BLOCKED: set[str] = set()


def block_ip(ip: str) -> bool:
    """
    Adds an IP to macOS pf firewall block table.
    Returns True if successful, False otherwise.
    """
    if not ENABLE_AUTO_BLOCK_IPS:
        logger.debug("Auto-block disabled — skipping block for %s", ip)
        return False

    if ip in _BLOCKED:
        logger.debug("IP %s already blocked", ip)
        return True

    try:
        cmd = f"echo 'block drop quick from {ip} to any' | sudo pfctl -ef -"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            _BLOCKED.add(ip)
            logger.warning("🚫 AUTO-BLOCKED IP: %s", ip)
            return True
        else:
            logger.error("pfctl block failed for %s: %s", ip, result.stderr)
            return False
    except Exception as e:
        logger.error("Auto-block error for %s: %s", ip, e)
        return False


def unblock_ip(ip: str) -> bool:
    """Remove an IP from the pf block table."""
    if ip not in _BLOCKED:
        return False
    try:
        result = subprocess.run(
            ["sudo", "pfctl", "-t", "cybercbp_blocked", "-T", "delete", ip],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            _BLOCKED.discard(ip)
            logger.info("✅ Unblocked IP: %s", ip)
            return True
    except Exception as e:
        logger.error("Unblock error for %s: %s", ip, e)
    return False


def get_blocked_ips() -> set[str]:
    return set(_BLOCKED)


__all__ = ["block_ip", "unblock_ip", "get_blocked_ips"]
