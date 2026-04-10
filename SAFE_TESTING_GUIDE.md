# 🔒 Safe Intrusion Testing Guide — CyberCBP

This guide shows you how to **safely test** detection rules without compromising your system.

---

## **Option 1: Run Built-in Unit Tests** ✅ SAFEST

These simulate threat scenarios **without actually doing anything dangerous**.

### Quick Test All

```bash
cd /Users/nihaldastagiri/Desktop/Cyber\ CBP
python3 tests/test_high_cpu.py
python3 tests/test_file_modification.py
python3 tests/test_suspicious_port.py
```

### What Each Test Does

#### **test_high_cpu.py** — Process CPU/Memory Monitoring
```bash
python3 tests/test_high_cpu.py
```
- ✅ Simulates a process using 95.5% CPU
- ✅ Simulates system memory at 92.3%
- ✅ Verifies `HIGH_CPU` and `HIGH_MEMORY` rules fire
- **No actual resource consumption**

**Expected Output:**
```
✅ PASS HIGH_CPU fired
✅ PASS HIGH_MEMORY fired
Results: ALL PASSED
```

#### **test_file_modification.py** — File Integrity Monitoring
```bash
python3 tests/test_file_modification.py
```
- ✅ Simulates writes to `/etc/hosts`, `/bin/new_binary`
- ✅ Simulates deletion of `/etc/passwd`
- ✅ Verifies `SENSITIVE_FILE_WRITE`, `SENSITIVE_FILE_DELETE` rules fire
- **No files actually modified**

**Expected Output:**
```
✅ PASS SENSITIVE_FILE_WRITE fired
✅ PASS SENSITIVE_FILE_DELETE fired
Results: 4/4 passed
```

#### **test_suspicious_port.py** — Network Detection
```bash
python3 tests/test_suspicious_port.py
```
- ✅ Simulates outbound connection to suspicious port 4444
- ✅ Simulates connection to blacklisted IP
- ✅ Verifies `SUSPICIOUS_PORT`, `BLACKLISTED_IP` rules fire
- **No actual network connections**

**Expected Output:**
```
✅ PASS SUSPICIOUS_PORT fired
✅ PASS BLACKLISTED_IP fired
Results: 2/2 passed
```

---

## **Option 2: Real-World Safe Simulations** ⚠️ USE WITH CAUTION

These create **temporary, isolated scenarios** to test detection.

### 2a. CPU Spike Testing

Create a safe CPU spike in a background process:

```bash
# Option 1: Use Python's cpu_count() for stress (safe, limited)
python3 << 'EOF'
import multiprocessing
import time

def cpu_burn():
    end = time.time() + 30  # Run for 30 seconds only
    while time.time() < end:
        _ = sum(i*i for i in range(1000000))

if __name__ == "__main__":
    with multiprocessing.Pool(2) as p:
        p.map(cpu_burn, [1, 2])
EOF
```

**Watch for HIGH_CPU alert in CyberCBP logs**

### 2b. Memory Spike Testing

Create a controlled memory spike:

```bash
python3 << 'EOF'
import time

# Allocate ~500MB temporarily
data = [0] * (125_000_000)  # ~500MB list
print(f"Allocated {len(data) * 8 / (1024**2):.0f} MB")
time.sleep(60)  # Hold for 60 seconds
print("Released")
EOF
```

**Watch for HIGH_MEMORY alert**

### 2c. Root Shell Spawning Test

Simulate a root shell (won't actually become root):

```bash
# This just tests if we *detect* it, doesn't actually do it
sudo bash -c "sleep 5 &"
```

**Watch for ROOT_SHELL_SPAWN alert (you'll need to run as sudo)**

### 2d. File Modification Test (Temporary Files Only)

Test on **temporary files, never system files**:

```bash
# Create a temporary test directory
mkdir -p /tmp/cybercbp-test
touch /tmp/cybercbp-test/testfile.txt

# Modify it (safe, it's temporary)
echo "modified" > /tmp/cybercbp-test/testfile.txt

# CyberCBP watches /etc, /bin, /usr/bin, /usr/local/bin, $HOME
# So this won't trigger alerts unless you configure WATCHED_PATHS to include /tmp
```

### 2e. Network Connection Test (Localhost Only)

Create a suspicious localhost connection:

```bash
# Terminal 1: Start a listener on suspicious port
nc -l 127.0.0.1 4444

# Terminal 2: Connect to it
python3 << 'EOF'
import socket
s = socket.socket()
s.connect(("127.0.0.1", 4444))
print("Connected to localhost:4444")
EOF
```

**Watch for SUSPICIOUS_PORT alert**

---

## **Option 3: Threat Intelligence Feed Testing** ✅ SAFE

Add test entries to threat feeds and verify detection:

```bash
# Add a test process name to suspicious_processes.txt
echo "test-malware" >> /Users/nihaldastagiri/Desktop/Cyber\ CBP/threat_intel/feeds/suspicious_processes.txt

# Add a test IP to malicious_ips.txt
echo "192.0.2.1" >> /Users/nihaldastagiri/Desktop/Cyber\ CBP/threat_intel/feeds/malicious_ips.txt

# Now if you see a process named "test-malware" or connect to 192.0.2.1,
# CyberCBP will generate BLACKLISTED_PROCESS / BLACKLISTED_IP alerts
```

**To verify it works (without actually running malware):**

```bash
python3 tests/test_suspicious_port.py  # Already tests this
```

---

## **Option 4: Full Integration Test** ⚠️ MOST REALISTIC

Run CyberCBP normally and let it detect **real legitimate activity**:

```bash
# Terminal 1: Start CyberCBP
python3 main.py

# Terminal 2: Perform normal activities and watch alerts
# Examples:
# - Open a browser (might trigger network alerts)
# - Run "top" (might trigger HIGH_CPU if system is busy)
# - Download files to $HOME (might trigger file_events)
# - SSH into a server (triggers network monitoring)
```

**Pros:** Real-world detection
**Cons:** May generate false positives for normal activity

---

## **Summary: Testing Recommended Order**

| Priority | Test | Command | Risk | Time |
|----------|------|---------|------|------|
| 1️⃣ | Unit Tests (all) | `python3 tests/*.py` | ✅ None | <1 min |
| 2️⃣ | Threat Feed Test | Modify `.txt` feeds | ✅ Safe | 1 min |
| 3️⃣ | CPU Spike | Python multiprocessing | ⚠️ Low | 1 min |
| 4️⃣ | Memory Spike | Python list allocation | ⚠️ Low | 1 min |
| 5️⃣ | Network Test | `nc -l` localhost | ✅ Safe | 1 min |
| 6️⃣ | Integration Test | Run `main.py` normally | ⚠️ Medium | ongoing |

---

## **❌ DO NOT TEST WITH**

- ❌ Actual malware/viruses
- ❌ Real data exfiltration
- ❌ Actual network attacks on other systems
- ❌ Modifying system files (`/etc`, `/bin`, `/usr/bin`)
- ❌ Deleting system files
- ❌ Port scanning other machines without permission
- ❌ Creating actual backdoors

---

## **✅ Monitoring During Tests**

Keep CyberCBP running while testing:

```bash
# Terminal 1: Start CyberCBP
python3 main.py

# Terminal 2: Run tests
python3 tests/test_high_cpu.py
python3 tests/test_file_modification.py
python3 tests/test_suspicious_port.py

# Watch Terminal 1 for:
# - 🟡 [MEDIUM] HIGH_CPU
# - 🟡 [MEDIUM] HIGH_MEMORY
# - 🔴 [HIGH] SENSITIVE_FILE_WRITE
# - 💀 [CRITICAL] SENSITIVE_FILE_DELETE
# - 🔴 [HIGH] SUSPICIOUS_PORT
# - 🔴 [HIGH] BLACKLISTED_IP
```

---

## **Database & Log Inspection**

After testing, inspect results:

```bash
# View all threat events from CLI
sqlite3 /Users/nihaldastagiri/Desktop/Cyber\ CBP/db/cybercbp.db \
  "SELECT rule_id, severity, description FROM threats LIMIT 10;"

# View logs
tail -100 /Users/nihaldastagiri/Desktop/Cyber\ CBP/cybercbp.log

# Export as JSON (via API)
curl http://localhost:5000/api/threats
```

---

## **Resetting Between Tests**

To clear test data:

```bash
# Stop CyberCBP (Ctrl+C)

# Clear database
rm /Users/nihaldastagiri/Desktop/Cyber\ CBP/db/cybercbp.db

# Remove test feeds (revert suspicious_processes.txt, etc.)
git checkout /Users/nihaldastagiri/Desktop/Cyber\ CBP/threat_intel/feeds/

# Restart
python3 main.py
```

---

**Happy testing! 🛡️**
