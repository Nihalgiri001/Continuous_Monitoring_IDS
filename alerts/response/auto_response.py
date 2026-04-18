"""
alerts/response/auto_response.py — Autonomous Response Engine

Risk-score driven response policy:
  - Medium: log only
  - High:   kill suspicious process (configurable)
  - Critical: block suspicious IP + kill process + quarantine file (when possible)

All actions are configurable in config.py and designed to fail safely.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import psutil

from config import (
    ENABLE_AUTONOMOUS_RESPONSE,
    AUTO_RESPONSE_SAFE_MODE,
    ENABLE_AUTO_KILL_PROCESSES,
    ENABLE_AUTO_BLOCK_IPS,
    QUARANTINE_DIR,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_CRITICAL,
)
from alerts.response.auto_block import block_ip

logger = logging.getLogger(__name__)


def _extract_suspect_pid(event) -> int | None:
    rd = getattr(event, "raw_data", {}) or {}
    for k in ("pid",):
        try:
            if rd.get(k) is not None:
                return int(rd.get(k))
        except Exception:
            pass
    # ML anomalies may carry snapshot_context with processes; choose top cpu process
    ctx = (rd.get("snapshot_context") or {})
    procs = ctx.get("processes") or []
    best = None
    for p in procs:
        try:
            cpu = float(p.get("cpu_percent") or 0.0)
            mem = float(p.get("memory_percent") or 0.0)
            score = cpu * 2.0 + mem
            if best is None or score > best[0]:
                best = (score, int(p.get("pid")), p)
        except Exception:
            continue
    return best[1] if best else None


def _extract_suspect_ip(event) -> str | None:
    rd = getattr(event, "raw_data", {}) or {}
    # direct raddr
    raddr = rd.get("raddr") or ""
    if isinstance(raddr, str) and ":" in raddr:
        return raddr.split(":")[0]
    # connections within snapshot_context: pick the most frequent remote ip
    ctx = (rd.get("snapshot_context") or {})
    conns = ctx.get("connections") or []
    counts: dict[str, int] = {}
    for c in conns:
        ra = c.get("raddr") or ""
        if not ra or ":" not in ra:
            continue
        ip = ra.split(":")[0]
        counts[ip] = counts.get(ip, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _extract_suspect_file(event) -> str | None:
    rd = getattr(event, "raw_data", {}) or {}
    src = rd.get("src")
    if isinstance(src, str) and src:
        return src
    # ML anomalies: choose the first file event path
    ctx = (rd.get("snapshot_context") or {})
    fes = ctx.get("file_events") or []
    for fe in fes:
        s = fe.get("src")
        if isinstance(s, str) and s:
            return s
    return None


def _kill_process(pid: int) -> bool:
    if not ENABLE_AUTO_KILL_PROCESSES:
        return False
    if AUTO_RESPONSE_SAFE_MODE:
        logger.warning("[SAFE MODE] Would kill process PID %d", pid)
        return True
    try:
        p = psutil.Process(pid)
        p.terminate()
        try:
            p.wait(timeout=3)
        except Exception:
            p.kill()
        logger.warning("🛑 AUTO-KILLED process PID %d", pid)
        return True
    except Exception as exc:
        logger.error("Auto-kill failed for PID %d: %s", pid, exc)
        return False


def _block_ip(ip: str) -> bool:
    if not ENABLE_AUTO_BLOCK_IPS:
        return False
    if AUTO_RESPONSE_SAFE_MODE:
        logger.warning("[SAFE MODE] Would block IP %s", ip)
        return True
    return bool(block_ip(ip))


def _quarantine_file(path: str) -> bool:
    if AUTO_RESPONSE_SAFE_MODE:
        logger.warning("[SAFE MODE] Would quarantine file %s", path)
        return True
    try:
        src = Path(path)
        if not src.exists() or not src.is_file():
            return False
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        dest = QUARANTINE_DIR / src.name
        # Avoid clobbering existing quarantine entries
        if dest.exists():
            dest = QUARANTINE_DIR / f"{src.name}.{int(psutil.boot_time())}"
        shutil.move(str(src), str(dest))
        try:
            os.chmod(str(dest), 0o600)
        except Exception:
            pass
        logger.warning("📦 QUARANTINED file %s → %s", src, dest)
        return True
    except Exception as exc:
        logger.error("Quarantine failed for %s: %s", path, exc)
        return False


class AutonomousResponseEngine:
    def respond(self, event, risk_score: int) -> str:
        """
        Executes best-effort response actions based on risk score.
        Returns a comma-separated action string (for DB/UI).
        """
        if not ENABLE_AUTONOMOUS_RESPONSE:
            return ""

        actions: list[str] = []

        if risk_score >= int(RISK_THRESHOLD_CRITICAL):
            ip = _extract_suspect_ip(event)
            pid = _extract_suspect_pid(event)
            fp = _extract_suspect_file(event)

            if ip and _block_ip(ip):
                actions.append(f"block_ip:{ip}")
            if pid is not None and _kill_process(pid):
                actions.append(f"kill_pid:{pid}")
            if fp and _quarantine_file(fp):
                actions.append(f"quarantine:{fp}")

        elif risk_score >= int(RISK_THRESHOLD_HIGH):
            pid = _extract_suspect_pid(event)
            if pid is not None and _kill_process(pid):
                actions.append(f"kill_pid:{pid}")

        # Medium: log only (no action), handled by caller via persistence/notifier chain
        return ",".join(actions)


__all__ = ["AutonomousResponseEngine"]

