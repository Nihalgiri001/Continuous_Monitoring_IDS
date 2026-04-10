# 🎯 CyberCBP Demo & Testing Index

## Quick Navigation

### 🚀 Getting Started
- **First time?** Start here: [DEMO_GUIDE.md](DEMO_GUIDE.md)
- **Want to run tests?** See: [TESTING_REFERENCE.md](TESTING_REFERENCE.md)
- **Need details?** Read: [SAFE_TESTING_GUIDE.md](SAFE_TESTING_GUIDE.md)

---

## 📦 Available Tools

### Demo Scripts

#### 1. **demo_suspicious_activity.py** (Interactive)
```bash
python3 demo_suspicious_activity.py
```
- ✅ Interactive menu with 9 scenarios
- ✅ Choose which attack to simulate
- ✅ Real-time detection watching
- ✅ Perfect for learning and demonstrations

**Scenarios:**
1. 🟡 HIGH_CPU (Mining/Brute Force)
2. 🟡 HIGH_MEMORY (Memory Bomb/DoS)
3. 🔴 SUSPICIOUS_PORT (Botnet C2)
4. 🔴 BLACKLISTED_IP (Exfiltration)
5. 🔴 FILE_WRITE (Rootkit/Backdoor)
6. 💀 FILE_DELETE (Ransomware)
7. 💀 ROOT_SHELL (Privilege Escalation)
8. 🟡 RAPID_CONNECTIONS (Port Scanning)
9. 🎯 MULTI_STAGE_ATTACK (Full APT Chain)

#### 2. **run_all_demos.sh** (Automated)
```bash
bash run_all_demos.sh
```
- ✅ Runs all 9 scenarios automatically
- ✅ No user interaction needed
- ✅ Pauses between scenarios
- ✅ Perfect for presentations/CI/CD

#### 3. **quick_test.sh** (Unit Tests)
```bash
bash quick_test.sh
```
- ✅ Runs 3 unit test files
- ✅ Validates all detection rules
- ✅ ~1 minute total
- ✅ Good for quick validation

---

## 📋 Testing Files

### Unit Tests
- `tests/test_high_cpu.py` - CPU/Memory detection
- `tests/test_file_modification.py` - File integrity
- `tests/test_suspicious_port.py` - Network detection

### Run All Tests
```bash
python3 tests/test_high_cpu.py
python3 tests/test_file_modification.py
python3 tests/test_suspicious_port.py
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **DEMO_GUIDE.md** | Complete demo documentation with all 9 scenarios |
| **TESTING_REFERENCE.md** | Quick reference for testing |
| **SAFE_TESTING_GUIDE.md** | Comprehensive safety testing procedures |
| **README.md** | Main project documentation |

---

## 🎯 Recommended Workflows

### For Quick Validation
```bash
# Terminal 1
python3 main.py

# Terminal 2
bash quick_test.sh
```
Time: ~1-2 minutes

### For Interactive Demo
```bash
# Terminal 1
python3 main.py

# Terminal 2
python3 demo_suspicious_activity.py
# Select scenario 9 for maximum impact
```
Time: ~5-20 minutes (depending on scenario)

### For Full Presentation
```bash
# Terminal 1
python3 main.py

# Terminal 2
bash run_all_demos.sh
```
Time: ~5-10 minutes for all scenarios
Result: ~40-50 total alerts generated

### For Database Validation
```bash
# After running any demo
sqlite3 db/cybercbp.db "SELECT rule_id, COUNT(*) FROM threats GROUP BY rule_id;"
sqlite3 db/cybercbp.db "SELECT severity, COUNT(*) FROM threats GROUP BY severity;"
```

---

## ✅ Success Criteria

### After Running demo_suspicious_activity.py (Scenario 9):

- ✅ 6 alerts appear in CyberCBP console
- ✅ Alerts appear within 2 seconds of injection
- ✅ Proper severity levels displayed
- ✅ Database contains threat events
- ✅ Log file records all detections

### Expected Alert Sequence:
1. 🟡 RAPID_CONNECTIONS (from reconnaissance)
2. 🟡 HIGH_CPU (from exploitation)
3. 💀 ROOT_SHELL_SPAWN (from escalation)
4. 🔴 SUSPICIOUS_PORT (from exfiltration)
5. 🔴 BLACKLISTED_IP (from C2)

---

## 🔒 Safety Notes

✅ **100% Safe:**
- No real malware executed
- No real system files modified
- No real network traffic outside localhost
- No real processes terminated
- Can be run repeatedly
- Fully isolated

❌ **Never:**
- Use against other systems
- Execute real attacks
- Modify production systems
- Deploy in untrusted environments

---

## 🛠️ Troubleshooting

### No alerts appearing?
1. Check CyberCBP is running: `ps aux | grep main.py`
2. Check logs: `tail -50 cybercbp.log`
3. Reset database: `rm db/cybercbp.db`
4. Restart CyberCBP: `python3 main.py`

### Demo script crashes?
1. Check error message
2. Verify CyberCBP running
3. Check Python version: `python3 --version`
4. Try again with verbose output: `python3 -u demo_suspicious_activity.py 2>&1 | tee demo.log`

### Alerts not matching expected output?
1. Check alert cooldown (60 seconds): `SELECT rule_id, timestamp FROM alerts ORDER BY timestamp DESC LIMIT 5;`
2. Clear database and retry: `rm db/cybercbp.db`
3. Check config.py thresholds
4. Review ALERT_COOLDOWN_SECONDS setting

---

## 📊 Database Queries

### View all threats
```bash
sqlite3 db/cybercbp.db "SELECT rule_id, severity, description FROM threats LIMIT 20;"
```

### Count by rule
```bash
sqlite3 db/cybercbp.db "SELECT rule_id, COUNT(*) FROM threats GROUP BY rule_id ORDER BY COUNT(*) DESC;"
```

### Count by severity
```bash
sqlite3 db/cybercbp.db "SELECT severity, COUNT(*) FROM threats GROUP BY severity;"
```

### Latest 10 threats
```bash
sqlite3 db/cybercbp.db "SELECT timestamp, rule_id, severity FROM threats ORDER BY id DESC LIMIT 10;"
```

### Export to JSON
```bash
sqlite3 db/cybercbp.db ".mode json" "SELECT * FROM threats LIMIT 50;" > threats.json
```

---

## 🚀 Next Steps

1. **First Run:**
   - Start CyberCBP
   - Run quick_test.sh
   - Verify all tests pass

2. **Interactive Learning:**
   - Run demo_suspicious_activity.py
   - Try each scenario individually
   - Watch console alerts in real-time

3. **Full Demonstration:**
   - Run run_all_demos.sh
   - Query database for results
   - Present findings to team

4. **Production Deployment:**
   - Review config.py thresholds
   - Adjust for your environment
   - Deploy to production monitoring

---

## 📞 Support Resources

- **Detection Rules:** See `detection/rules_engine.py`
- **Alert Management:** See `alerts/alert_manager.py`
- **Configuration:** See `config.py`
- **Threat Intelligence:** See `threat_intel/intel_manager.py`
- **ML Detection:** See `ml_engine/detector.py`

---

**Ready to demonstrate? Pick a workflow above and get started! 🛡️**
