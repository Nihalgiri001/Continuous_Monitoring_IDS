"""
threat_intel/virustotal.py — VirusTotal API Integration (optional)

Performs file hash lookups against the VirusTotal API v3.
Gracefully disabled when VT_API_KEY is not set in environment.

Usage:
    from threat_intel.virustotal import check_hash
    result = check_hash("sha256_hash_here")
"""

import logging
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VIRUSTOTAL_API_KEY

logger = logging.getLogger(__name__)

_VT_BASE = "https://www.virustotal.com/api/v3"
_CACHE: dict[str, dict] = {}
_RATE_LIMIT_DELAY = 16   # VT free tier: 4 req/min → wait 16s between calls


def check_hash(sha256: str) -> dict | None:
    """
    Look up a file hash on VirusTotal.
    Returns a result dict or None if disabled/unavailable.
    """
    if not VIRUSTOTAL_API_KEY:
        logger.debug("VirusTotal disabled — set VT_API_KEY env var to enable")
        return None

    sha256 = sha256.lower()
    if sha256 in _CACHE:
        return _CACHE[sha256]

    try:
        import requests
        headers = {"x-apikey": VIRUSTOTAL_API_KEY}
        url = f"{_VT_BASE}/files/{sha256}"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            result = {
                "hash": sha256,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "harmless":   stats.get("harmless", 0),
                "undetected": stats.get("undetected", 0),
                "is_malicious": stats.get("malicious", 0) > 0,
            }
            _CACHE[sha256] = result
            if result["is_malicious"]:
                logger.warning(
                    "VirusTotal: %s flagged by %d engines",
                    sha256[:16], result["malicious"]
                )
            time.sleep(_RATE_LIMIT_DELAY)
            return result

        elif resp.status_code == 404:
            logger.debug("VT: hash not found — %s", sha256[:16])
            return None
        elif resp.status_code == 429:
            logger.warning("VirusTotal rate limit hit — slow down requests")
            return None
        else:
            logger.warning("VT API error %d for hash %s", resp.status_code, sha256[:16])
            return None

    except ImportError:
        logger.warning("requests library needed for VirusTotal — pip install requests")
        return None
    except Exception as e:
        logger.error("VirusTotal lookup failed: %s", e)
        return None


__all__ = ["check_hash"]
