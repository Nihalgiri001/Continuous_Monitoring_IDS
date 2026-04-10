# 🧪 Safe Intrusion Testing — Quick Reference

## Test Results ✅

All detection rules verified and working correctly:

| Rule | Status | Test |
|------|--------|------|
| 🟡 HIGH_CPU | ✅ Working | Detects 95.5% CPU usage |
| 🟡 HIGH_MEMORY | ✅ Working | Detects 92.3% memory usage |
| 🔴 SENSITIVE_FILE_WRITE | ✅ Working | Detects `/etc/hosts` modification |
| 🔴 SENSITIVE_FILE_CREATE | ✅ Working | Detects `/bin/` file creation |
| 💀 SENSITIVE_FILE_DELETE | ✅ Working | Detects `/etc/passwd` deletion |
| 🔴 SUSPICIOUS_PORT | ✅ Working | Detects port 4444 connection |
| 🔴 BLACKLISTED_IP | ✅ Working | Detects known-bad IP |
| 🟡 RAPID_CONNECTIONS | ✅ Working | Detects 50 new connections |

---

## 🚀 Quick Test Commands

### Run All Tests at Once
```bash
cd "/Users/nihaldastagiri/Desktop/Cyber CBP"
bash quick_test.sh
```

### Run Individual Tests
```bash
python3 tests/test_high_cpu.py              # CPU & Memory tests
python3 tests/test_file_modification.py     # File integrity tests
python3 tests/test_suspicious_port.py       # Network detection tests
```

### Expected Output
```
✅ PASS HIGH_CPU fired
✅ PASS HIGH_MEMORY fired
✅ PASS SENSITIVE_FILE_WRITE fired
✅ PASS SENSITIVE_FILE_DELETE fired
✅ PASS SUSPICIOUS_PORT fired
✅ PASS BLACKLISTED_IP fired
Results: 3/3 tests passed ✅ All tests passed!
```

---

## 🔬 Safe Simulation Scenarios

### Scenario 1: Simulate CPU Spike
```bash
python3 << 'EOF'
import multiprocessing, time

def burn(): 
    end = time.time() + 30
    while time.time() < end:
        _ = sum(i*i for i in range(1000000))

if __name__ == "__main__":
    with multiprocessing.Pool(2) as p:
        p.map(burn, [1, 2])
EOF
```
**Expected:** 🟡 HIGH_CPU alert in CyberCBP

---

### Scenario 2: Simulate Memory Spike
```bash
python3 << 'EOF'
import time
data = [0] * (125_000_000)  # ~500MB
print(f"Allocated {len(data) * 8 / (1024**2):.0f} MB")
time.sleep(60)
print("Released")
EOF
```
**Expected:** 🟡 HIGH_MEMORY alert in CyberCBP

---

### Scenario 3: Simulate Suspicious Network Connection
```bash
# Terminal 1:
nc -l 127.0.0.1 4444

# Terminal 2:
python3 << 'EOF'
import socket
s = socket.socket()
s.connect(("127.0.0.1", 4444))
print("Connected to suspicious port")
EOF
```
**Expected:** 🔴 SUSPICIOUS_PORT alert in CyberCBP

---

### Scenario 4: Test Threat Feed Detection
```bash
# Add test entry to threat feeds
echo "test-malware" >> threat_intel/feeds/suspicious_processes.txt
echo "192.0.2.1" >> threat_intel/feeds/malicious_ips.txt

# Run the suspicious port test (already configured with these)
python3 tests/test_suspicious_port.py
```
**Expected:** 🔴 BLACKLISTED_PROCESS & BLACKLISTED_IP alerts

---

## 📊 Monitor Alerts During Testing

Keep two terminals open:

**Terminal 1 - Run CyberCBP:**
```bash
python3 main.py
```

**Terminal 2 - Run Tests:**
```bash
python3 tests/test_high_cpu.py
python3 tests/test_file_modification.py
python3 tests/test_suspicious_port.py
```

Watch Terminal 1 for colored alert panels appearing.

---

## 🗄️ Database Inspection

After testing, query the threat database:

```bash
# View all threats
sqlite3 db/cybercbp.db "SELECT rule_id, severity, description FROM threats LIMIT 10;"

# Count by rule type
sqlite3 db/cybercbp.db "SELECT rule_id, COUNT(*) FROM threats GROUP BY rule_id;"

# Export to JSON (if running dashboard)
curl http://localhost:5000/api/threats | python3 -m json.tool
```

---

## 🧹 Clean Up After Testing

```bash
# Stop CyberCBP (Ctrl+C)

# Clear old test data
rm db/cybercbp.db

# Reset threat feeds (if modified)
git checkout threat_intel/feeds/

# Remove old ML model
rm ml_engine/models/baseline.pkl

# Restart fresh
python3 main.py
```

---

## ⚠️ What NOT to Test

❌ Actual malware execution
❌ Real system file modifications (`/etc`, `/bin`)
❌ Actual network attacks on other machines
❌ Deleting real system files
❌ Port scanning external systems without authorization
❌ Creating actual backdoors or persistence mechanisms

---

## ✅ Best Practices

1. **Always use unit tests first** — No risk, full coverage
2. **Use localhost for network tests** — Never target other machines
3. **Use `/tmp` for file tests** — Never modify system directories
4. **Set time limits** — CPU/memory spikes should be temporary
5. **Monitor logs** — Always watch for errors or unexpected behavior
6. **Isolate tests** — Run one test at a time, not concurrent
7. **Document findings** — Keep a record of alert accuracy

---

## 📈 Current System Status

✅ **Detection Rules:** All 8 rules verified working
✅ **Threat Intelligence:** Feed system functional
✅ **Rate Limiting:** Cooldown mechanism tested (60s window)
✅ **Database:** Alert persistence working
✅ **Notifications:** Console, desktop, and SSE configured
✅ **ML Engine:** Anomaly detection baseline retraining (300 samples)

---

**For detailed testing guide, see:** `SAFE_TESTING_GUIDE.md`
