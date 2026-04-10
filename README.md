# CyberCBP — Proactive Cybersecurity Threat Detection & Vulnerability Monitoring System

A modular, production-inspired cybersecurity tool that runs continuously on your machine, monitors system activity in real-time, detects threats using rule-based and ML-based techniques, and surfaces everything through a live dashboard.

---

## 🏗 Architecture

```
System Data → Monitoring Agent → event_queue → Rules Engine  ┐
                                             → ML Detector   ├→ threat_queue → Alert Manager → Dashboard (SSE)
File Watcher ──────────────────────────────────────────────────┘                             → DB
Port Scanner → vuln_queue ────────────────────────────────────────────────────────────────→ Alert Manager
Threat Intel ← IntelManager (loaded from feeds/) ← rules engine queries
```

### Module Map

| Module | Path | Purpose |
|--------|------|---------|
| Monitoring Agent | `agent/monitor.py` | Collects CPU, memory, process, network snapshots |
| File Watcher | `agent/file_watcher.py` | Watchdog events on critical paths |
| Event Queue | `core/event_queue.py` | Central `queue.Queue` pipeline — decouples all modules |
| Severity Scoring | `core/severity.py` | LOW/MEDIUM/HIGH/CRITICAL/ANOMALY with per-rule map |
| Rule-Based IDS | `detection/rules_engine.py` | 8 built-in detection rules |
| ML Engine | `ml_engine/` | IsolationForest anomaly detection |
| Threat Intel | `threat_intel/` | IP/domain/process/hash blacklists |
| Port Scanner | `scanner/port_scanner.py` | nmap + socket fallback + risky port mapping |
| Config Auditor | `scanner/config_auditor.py` | SSH, firewall, world-writable checks |
| Alert Manager | `alerts/alert_manager.py` | Rate-limited, dedup'd notifier dispatch |
| Console Notifier | `alerts/notifiers/console.py` | Rich color-coded terminal output |
| Desktop Notifier | `alerts/notifiers/desktop.py` | macOS native notifications |
| Report Exporter | `reports/exporter.py` | JSON + CSV export |
| Dashboard | `dashboard/` | Flask API + real-time SSE frontend |
| Database | `db/database.py` | SQLite persistence |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd "Cyber CBP"
pip install -r requirements.txt
```

> **Optional**: Install `nmap` for enhanced port scanning:
> ```bash
> brew install nmap
> ```

### 2. Run the system

```bash
python main.py
```

The system will:
1. Start all modules
2. Collect baseline data for ML training (~5 minutes)
3. Begin active anomaly detection
4. Open the dashboard at **http://127.0.0.1:5000**

### 3. Run tests

```bash
# All three test suites
python tests/test_high_cpu.py
python tests/test_suspicious_port.py
python tests/test_file_modification.py
```

---

## 🎛 Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `MONITORING_INTERVAL_SECONDS` | `5` | How often to collect snapshots |
| `CPU_ALERT_THRESHOLD` | `85.0` | % CPU per process to trigger alert |
| `MEMORY_ALERT_THRESHOLD` | `90.0` | % total RAM to trigger alert |
| `ALERT_COOLDOWN_SECONDS` | `60` | Rate-limit window between duplicate alerts |
| `SCAN_INTERVAL_SECONDS` | `300` | Port scan frequency |
| `ML_WARMUP_SAMPLES` | `60` | Snapshots to collect before ML training |
| `ENABLE_DESKTOP_NOTIFICATIONS` | `True` | macOS native notifications |
| `ENABLE_AUTO_BLOCK_IPS` | `False` | Auto-block via pfctl (needs sudo) |

### Optional: VirusTotal Integration

```bash
export VT_API_KEY="your_api_key_here"
python main.py
```

### Optional: Email Alerts

```bash
export SMTP_HOST="smtp.gmail.com"
export ALERT_EMAIL_SENDER="you@gmail.com"
export ALERT_EMAIL_RECIPIENT="you@gmail.com"
export ALERT_EMAIL_PASSWORD="app_password"
```
Then set `ENABLE_EMAIL_ALERTS = True` in `config.py`.

---

## 📊 Dashboard Features

Visit **http://127.0.0.1:5000**

- **System Health Panel** — live CPU, memory, connection gauges
- **Threat Severity Breakdown** — Critical / High / Medium / Low counts
- **Live Threat Feed** — real-time SSE-pushed events with severity filter
- **Vulnerability Report** — open ports with risk descriptions, sortable by severity
- **Threat Intelligence Stats** — counts from all blacklist feeds
- **Threats Over Time Chart** — Chart.js timeline
- **⚡ Scan Now** — on-demand vulnerability scan
- **📥 Export** — one-click JSON + CSV report export

---

## 🔍 Detection Rules

| Rule ID | Trigger | Severity |
|---------|---------|---------|
| `HIGH_CPU` | Process CPU > 85% | Medium |
| `HIGH_MEMORY` | System RAM > 90% | Medium |
| `BLACKLISTED_PROCESS` | Process name in feed | High |
| `BLACKLISTED_IP` | Connection to known-bad IP | High |
| `SUSPICIOUS_PORT` | Outbound to port 4444, 1337, 6666, etc. | High |
| `RAPID_CONNECTIONS` | >30 new connections / interval | Medium |
| `SENSITIVE_FILE_WRITE` | Modify in `/etc`, `/bin`, etc. | High |
| `SENSITIVE_FILE_DELETE` | Delete from sensitive path | Critical |
| `ROOT_SHELL_SPAWN` | bash/sh running as root | Critical |
| `ML_ANOMALY` | IsolationForest score < threshold | Anomaly |

---

## 🔌 Risky Port Risk Map (sample)

| Port | Risk |
|------|------|
| 21 | FTP — plaintext credentials |
| 23 | Telnet — fully unencrypted |
| 445 | SMB — EternalBlue target |
| 3389 | RDP — BlueKeep target |
| 4444 | Metasploit default listener |
| 6379 | Redis — often no auth |
| 31337 | Back Orifice — critical |

---

## 📁 Project Structure

```
Cyber CBP/
├── main.py                    # Orchestrator
├── config.py                  # Central configuration
├── requirements.txt
├── cybercbp.log               # Runtime log (auto-created)
├── core/
│   ├── event_queue.py         # Central queue.Queue pipeline
│   ├── severity.py            # Severity scoring system
│   └── threat_event.py        # ThreatEvent + SystemSnapshot dataclasses
├── agent/
│   ├── monitor.py             # System snapshot collector
│   └── file_watcher.py        # Watchdog file event monitor
├── detection/
│   └── rules_engine.py        # Rule-based IDS (8 rules)
├── ml_engine/
│   ├── trainer.py             # IsolationForest baseline trainer
│   ├── detector.py            # Live anomaly scoring
│   └── models/                # Persisted model artifacts
├── threat_intel/
│   ├── intel_manager.py       # Blacklist manager
│   ├── virustotal.py          # Optional VT API
│   └── feeds/                 # IP / domain / process / hash feeds
├── scanner/
│   ├── port_scanner.py        # nmap + socket scanner + risk map
│   └── config_auditor.py      # SSH / firewall / file permission checks
├── alerts/
│   ├── alert_manager.py       # Rate-limited dispatcher
│   ├── notifiers/
│   │   ├── console.py         # Rich terminal output
│   │   └── desktop.py         # macOS native notifications
│   └── response/
│       └── auto_block.py      # pfctl IP blocker (disabled by default)
├── reports/
│   ├── exporter.py            # JSON + CSV export engine
│   └── exports/               # Generated report files
├── dashboard/
│   ├── app.py                 # Flask API + SSE server
│   └── templates/
│       └── index.html         # Real-time dashboard UI
├── db/
│   ├── database.py            # SQLite schema + helpers
│   └── cybercbp.db            # Database (auto-created)
└── tests/
    ├── test_high_cpu.py
    ├── test_suspicious_port.py
    └── test_file_modification.py
```

---

## ⚠️ Notes

- **macOS permissions**: Some features need Full Disk Access (System Preferences → Privacy). The system degrades gracefully without it.
- **Auto-block**: Disabled by default. Requires `sudo` and explicit opt-in in `config.py`.
- **ML warm-up**: The IsolationForest trains on your first 60 snapshots (~5 minutes at 5s intervals). Anomaly detection activates after training.
- **OpenVAS**: Stubbed — wire in `scanner/openvas_stub.py` once you have an OpenVAS server running.

---

## 📜 License

MIT — for educational and research purposes.
