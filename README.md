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
# CyberCBP — Continuous Monitoring IDS with ML Training Infrastructure

A modular, production-inspired continuous monitoring system that detects threats using deterministic rules plus an IsolationForest-based anomaly detector. This README reflects the latest ML training infrastructure: long-running data collection, batch training, and documentation to produce expert-level models.

---

## Key additions

- ML training infrastructure: `collect_training_data.py`, `train_on_historical.py`, and `ml_engine/historical_collector.py`.
- Comprehensive ML docs: `ML_START_HERE.md`, `ML_TRAINING_WORKFLOW.md`, `ML_TRAINING_QUICK_REFERENCE.md`, `ML_INFRASTRUCTURE_SUMMARY.md`, `ML_DOCUMENTATION_INDEX.md`.
- `ml_engine/data/` (historical snapshots) and `ml_engine/models/` (trained models) directories.
- Recommended warmup increased to 600 samples (see `config.py`).

---

## 🚀 Quick Start (choose one)

Install dependencies:

```bash
cd "Cyber CBP"
pip install -r requirements.txt
# Optional (macOS): brew install nmap
```

Method 1 — Quick (50 minutes)

```bash
python3 main.py
```

• Auto-collects ~600 warmup samples (≈50 min at 5s interval). The system trains a baseline model and starts anomaly detection automatically.

Method 2 — Production (overnight, recommended)

```bash
mkdir -p ml_engine/data ml_engine/models
nohup python3 collect_training_data.py --hours 8 > collection.log 2>&1 &
# Next morning
python3 train_on_historical.py
cp ml_engine/models/historical_baseline.pkl ml_engine/models/baseline.pkl
python3 main.py
```

Method 3 — Continuous (advanced)

Edit `config.py`:

```python
ML_USE_HISTORICAL = True
```

Then run `python3 main.py` — the trainer will integrate historical data when available.

---

## 🔧 Configuration highlights (`config.py`)

- `MONITORING_INTERVAL_SECONDS`: 5
- `ML_WARMUP_SAMPLES`: 600
- `ML_CONTAMINATION`: 0.01
- `ML_ANOMALY_SCORE_THRESHOLD`: -0.10
- `ML_USE_HISTORICAL`: False
- `ALERT_COOLDOWN_SECONDS`: 60

See `config.py` for full options.

---

## 🧭 ML Training Flow (quick)

- `collect_training_data.py` — collects periodic snapshots into `.npy` checkpoint files under `ml_engine/data/`.
- `train_on_historical.py` — loads all `.npy` snapshot files, trains an IsolationForest, and saves to `ml_engine/models/historical_baseline.pkl`.
- Deploy by copying the trained model to `ml_engine/models/baseline.pkl` or updating the detector to load the new path.

Recommended: collect 4–8 hours of diverse normal activity for a robust model (4k–5k samples). For quick testing, use `--hours 0.1`.

---

## 🔍 Detection Rules

The system combines deterministic rule-based detections and ML:

- `HIGH_CPU`, `HIGH_MEMORY`, `BLACKLISTED_PROCESS`, `BLACKLISTED_IP`, `SUSPICIOUS_PORT`, `RAPID_CONNECTIONS`, `SENSITIVE_FILE_WRITE/DELETE`, `ROOT_SHELL_SPAWN`, `ML_ANOMALY`.

---

## � Project layout (updated)

```
Cyber CBP/
├── main.py
├── config.py
├── collect_training_data.py
├── train_on_historical.py
├── ml_engine/
│   ├── historical_collector.py
│   ├── trainer.py
│   ├── detector.py
│   ├── data/
│   └── models/
├── alerts/
├── agent/
├── detection/
├── scanner/
├── threat_intel/
├── dashboard/
├── reports/
├── db/
└── tests/
```

---

## ✅ Quick commands

Collect a short dataset (6 minutes):

```bash
python3 collect_training_data.py --hours 0.1
```

Train on collected data:

```bash
python3 train_on_historical.py
```

Deploy trained model:

```bash
cp ml_engine/models/historical_baseline.pkl ml_engine/models/baseline.pkl
python3 main.py
```

---

## 🧾 Documentation

See the new ML documentation in repo root:

- `ML_START_HERE.md` — main entry point
- `ML_TRAINING_WORKFLOW.md` — full step-by-step guide
- `ML_TRAINING_QUICK_REFERENCE.md` — quick cheat sheet
- `ML_INFRASTRUCTURE_SUMMARY.md` — implementation notes
- `ML_DOCUMENTATION_INDEX.md` — navigation index

---

## ⚠️ Notes and safety

- Do not commit `ml_engine/data/` or `ml_engine/models/` to public repos; they may contain local metadata. A `.gitignore` file is included.
- Auto-block is disabled by default and requires sudo and explicit opt-in.
- Some features need macOS permissions (Full Disk Access).

---

## 🧪 Tests

Run unit tests:

```bash
python3 -m pytest tests/
```

---

## 📜 License

MIT — for educational and research purposes.
