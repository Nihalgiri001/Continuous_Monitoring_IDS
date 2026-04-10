"""
threat_intel/intel_manager.py — Threat Intelligence Module

Loads and maintains blacklists for:
  - Malicious IPs
  - Malicious domains
  - Suspicious process names
  - Known malware file hashes

Provides fast O(1) lookup APIs used by the rules engine and scanner.
Refreshes feeds on a configurable schedule.
"""

import logging
import threading
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import THREAT_INTEL_DIR, INTEL_REFRESH_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


class IntelManager(threading.Thread):
    """
    Loads threat feeds from flat text files (one entry per line, # = comment).
    Refreshes periodically in the background.
    """

    daemon = True

    def __init__(self, feeds_dir: Path = THREAT_INTEL_DIR):
        super().__init__(name="IntelManager")
        self._feeds_dir = feeds_dir
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        # Lookup sets — populated by _refresh()
        self._bad_ips:      set[str] = set()
        self._bad_domains:  set[str] = set()
        self._bad_procs:    set[str] = set()
        self._bad_hashes:   set[str] = set()

        self._refresh()          # Load immediately on startup

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_feed(self, filename: str) -> set[str]:
        path = self._feeds_dir / filename
        if not path.exists():
            logger.debug("Feed file not found: %s", path)
            return set()
        entries: set[str] = set()
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    entries.add(line.lower())
        logger.debug("Loaded %d entries from %s", len(entries), filename)
        return entries

    def _refresh(self):
        with self._lock:
            self._bad_ips     = self._load_feed("malicious_ips.txt")
            self._bad_domains = self._load_feed("malicious_domains.txt")
            self._bad_procs   = self._load_feed("suspicious_processes.txt")
            self._bad_hashes  = self._load_feed("malware_hashes.txt")
        logger.info(
            "Threat intel refreshed — IPs:%d  Domains:%d  Procs:%d  Hashes:%d",
            len(self._bad_ips), len(self._bad_domains),
            len(self._bad_procs), len(self._bad_hashes),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def is_blacklisted_ip(self, ip: str) -> bool:
        with self._lock:
            return ip.lower() in self._bad_ips

    def is_malicious_domain(self, domain: str) -> bool:
        with self._lock:
            domain = domain.lower().rstrip(".")
            return domain in self._bad_domains or any(
                domain.endswith("." + d) for d in self._bad_domains
            )

    def is_suspicious_process(self, name: str) -> bool:
        with self._lock:
            return name.lower() in self._bad_procs

    def is_known_malware_hash(self, sha256: str) -> bool:
        with self._lock:
            return sha256.lower() in self._bad_hashes

    def stats(self) -> dict:
        with self._lock:
            return {
                "malicious_ips":    len(self._bad_ips),
                "malicious_domains": len(self._bad_domains),
                "suspicious_processes": len(self._bad_procs),
                "malware_hashes":   len(self._bad_hashes),
            }

    # ── Thread loop ───────────────────────────────────────────────────────────

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("IntelManager started (refresh every %ds)",
                    INTEL_REFRESH_INTERVAL_SECONDS)
        while not self._stop_event.is_set():
            self._stop_event.wait(INTEL_REFRESH_INTERVAL_SECONDS)
            if not self._stop_event.is_set():
                self._refresh()
        logger.info("IntelManager stopped")


__all__ = ["IntelManager"]
