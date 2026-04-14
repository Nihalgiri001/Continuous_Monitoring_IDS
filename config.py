"""
config.py — Central Configuration for CyberCBP
All tuneable parameters in one place.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "cybercbp.db"
MODEL_PATH = BASE_DIR / "ml_engine" / "models" / "baseline.pkl"
REPORTS_DIR = BASE_DIR / "reports" / "exports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Critical paths to watch for unauthorized modifications
WATCHED_PATHS = [
    "/etc",
    "/bin",
    "/usr/bin",
    "/usr/local/bin",
    str(Path.home()),
]

# ──────────────────────────────────────────────
# Monitoring Engine
# ──────────────────────────────────────────────
MONITORING_INTERVAL_SECONDS = 5        # How often to collect a system snapshot
ML_WARMUP_SAMPLES = 600               # Samples to collect before training ML model (increased from 30)
ML_CONTAMINATION = 0.01               # Expected fraction of anomalies (1%, reduced from 5%)
# NOTE: Score thresholds are now auto-calibrated from warm-up baseline when possible.
# The static threshold remains as a fallback for legacy models.
ML_ANOMALY_SCORE_THRESHOLD = -0.10    # Fallback: IsolationForest score below this = anomaly
ML_ANOMALY_SCORE_QUANTILE = 0.001     # Calibrated threshold = this quantile of baseline scores (lower = less alerts)
ML_ANOMALY_CONSECUTIVE_HITS = 3       # Require N consecutive anomalous scores before raising ML_ANOMALY

# ──────────────────────────────────────────────
# Rule-Based Detection Thresholds
# ──────────────────────────────────────────────
CPU_ALERT_THRESHOLD = 85.0            # % CPU per-process to trigger HIGH_CPU alert
MEMORY_ALERT_THRESHOLD = 90.0         # % total memory to trigger HIGH_MEM alert
RAPID_CONNECTION_THRESHOLD = 30       # New connections/interval from one PID
SUSPICIOUS_PORTS = {4444, 1337, 6666, 31337, 8888, 9999, 12345}

# ──────────────────────────────────────────────
# Alert & Response
# ──────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS = 60           # Min seconds between duplicate alerts (rate limiting)
ENABLE_DESKTOP_NOTIFICATIONS = True
ENABLE_EMAIL_ALERTS = False
EMAIL_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("ALERT_EMAIL_SENDER", "")
EMAIL_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "")
EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")

# Auto-response (disabled by default — requires sudo for pfctl)
ENABLE_AUTO_BLOCK_IPS = False
ENABLE_AUTO_KILL_PROCESSES = False

# ──────────────────────────────────────────────
# Vulnerability Scanner
# ──────────────────────────────────────────────
SCAN_TARGET = "127.0.0.1"
SCAN_INTERVAL_SECONDS = 300           # Run full scan every 5 minutes
NMAP_TIMEOUT_SECONDS = 60
NMAP_ARGS = "-sV --version-intensity 2 -T4"

# Risky port → risk description mapping
RISKY_PORTS = {
    21:   "FTP — transmits credentials in plaintext",
    22:   "SSH — ensure key-based auth & no root login",
    23:   "Telnet — fully unencrypted protocol",
    25:   "SMTP — can be abused for spam relay",
    53:   "DNS — potential for DNS amplification attacks",
    80:   "HTTP — unencrypted web traffic",
    110:  "POP3 — transmits mail credentials in plaintext",
    135:  "RPC — common Windows exploit target",
    139:  "NetBIOS — legacy, frequently exploited",
    143:  "IMAP — credentials sent in plaintext",
    445:  "SMB — EternalBlue & WannaCry attack surface",
    512:  "rexec — deprecated remote exec, no auth encryption",
    513:  "rlogin — insecure remote login",
    514:  "rsh — no authentication",
    1433: "MSSQL — database port should not be public",
    1521: "Oracle DB — database port should not be public",
    2049: "NFS — check exports, often misconfigured",
    3306: "MySQL — database port should not be public",
    3389: "RDP — brute-force and BlueKeep target",
    4444: "Metasploit default listener — high risk",
    5432: "PostgreSQL — database port should not be public",
    5900: "VNC — often weak auth",
    6379: "Redis — frequently exposed without auth",
    6666: "IRC / Trojan port — high risk",
    8080: "HTTP alt — check for unauth admin panels",
    8443: "HTTPS alt — verify certificate validity",
    9200: "Elasticsearch — often exposed without auth",
    27017: "MongoDB — frequently exposed without auth",
    31337: "Back Orifice / hacker port — critical risk",
}

# ──────────────────────────────────────────────
# Threat Intelligence
# ──────────────────────────────────────────────
THREAT_INTEL_DIR = BASE_DIR / "threat_intel" / "feeds"
VIRUSTOTAL_API_KEY = os.getenv("VT_API_KEY", "")  # Leave blank to disable
INTEL_REFRESH_INTERVAL_SECONDS = 3600  # Refresh blacklists every hour

# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000
DASHBOARD_DEBUG = False
MAX_THREATS_IN_UI = 200               # Max threat events shown in dashboard

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "cybercbp.log"
