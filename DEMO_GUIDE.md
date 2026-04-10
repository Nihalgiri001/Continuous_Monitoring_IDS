# 🎯 CyberCBP — Interactive Suspicious Activity Demo

## Overview

This is a **live demonstration tool** that simulates realistic attack scenarios and shows CyberCBP's detection capabilities in real-time.

**Perfect for:**
- ✅ Proving the system works
- ✅ Demonstrating to stakeholders/security team
- ✅ Testing detection capabilities
- ✅ Training purposes
- ✅ Validating alert accuracy

---

## 🚀 Quick Start (2-Terminal Setup)

### Terminal 1: Run CyberCBP
```bash
cd "/Users/nihaldastagiri/Desktop/Cyber CBP"
python3 main.py
```

You'll see the startup banner and then the monitoring loop begins.

### Terminal 2: Run the Demo
```bash
cd "/Users/nihaldastagiri/Desktop/Cyber CBP"
python3 demo_suspicious_activity.py
```

An interactive menu appears. Select a scenario (1-9) and watch Terminal 1 for real-time alerts.

---

## 📋 Available Attack Scenarios

### **Scenario 1: 🟡 HIGH_CPU Attack**
**Real-world Example:** Cryptocurrency mining malware, password cracking, DDoS zombie

**What it does:**
- Simulates a process consuming 87.5% CPU
- Mimics a mining bot named `mining-bot`

**Expected CyberCBP Alert:**
```
🟡 [MEDIUM] HIGH_CPU
   Process 'mining-bot' (PID 9999) is using 87.5% CPU
```

**Demo time:** ~30 seconds

---

### **Scenario 2: 🟡 HIGH_MEMORY Attack**
**Real-world Example:** Memory bomb, memory leak, resource exhaustion DoS

**What it does:**
- Shows system memory at 91.5% capacity
- Simulates process allocating large chunks of RAM

**Expected CyberCBP Alert:**
```
🟡 [MEDIUM] HIGH_MEMORY
   System memory at 91.5% (only 256.0 MB free)
```

**Demo time:** ~30 seconds

---

### **Scenario 3: 🔴 SUSPICIOUS_PORT Attack**
**Real-world Example:** Botnet C2 communication, backdoor callback

**What it does:**
- Simulates outbound connection to port 4444 (common botnet/backdoor port)
- Shows a process named `trojan` connecting to `198.51.100.45:4444`

**Expected CyberCBP Alert:**
```
🔴 [HIGH] SUSPICIOUS_PORT
   Outbound connection to suspicious port 4444 (raddr: 198.51.100.45:4444)
```

**Demo time:** ~2 seconds (instant)

---

### **Scenario 4: 🔴 BLACKLISTED_IP Attack**
**Real-world Example:** Command & control server connection, data exfiltration

**What it does:**
- Adds a test IP to threat intelligence blacklist
- Simulates connection to that blacklisted IP (203.0.113.50)

**Expected CyberCBP Alert:**
```
🔴 [HIGH] BLACKLISTED_IP
   Connection to blacklisted IP: 203.0.113.50
```

**Demo time:** ~2 seconds

---

### **Scenario 5: 🔴 FILE_WRITE Attack**
**Real-world Example:** Rootkit installation, SSH backdoor, privilege escalation

**What it does:**
- Simulates unauthorized modifications to:
  - `/etc/hosts` (DNS hijacking)
  - `/etc/ssh/authorized_keys` (persistent SSH access)
  - `/bin/ls` (rootkit installation)

**Expected CyberCBP Alert:**
```
🔴 [HIGH] SENSITIVE_FILE_WRITE
   Sensitive path modifyd: /etc/hosts
   Sensitive path modifyd: /etc/ssh/authorized_keys
   Sensitive path modifyd: /bin/ls
```

**Demo time:** ~2 seconds

---

### **Scenario 6: 💀 FILE_DELETE Attack (CRITICAL)**
**Real-world Example:** Ransomware, data destruction, sabotage

**What it does:**
- Simulates deletion of critical system files:
  - `/etc/passwd` (user database destruction)
  - `/etc/shadow` (password hashes destruction)
  - `/bin/sh` (shell removal)

**Expected CyberCBP Alert:**
```
💀 [CRITICAL] SENSITIVE_FILE_DELETE
   File deleted from sensitive path: /etc/passwd
   File deleted from sensitive path: /etc/shadow
   File deleted from sensitive path: /bin/sh
```

**Demo time:** ~2 seconds

---

### **Scenario 7: 💀 ROOT_SHELL_SPAWN (CRITICAL)**
**Real-world Example:** Successful privilege escalation, exploitation success

**What it does:**
- Simulates `bash` shell running with root privileges
- Indicates attacker has full system control

**Expected CyberCBP Alert:**
```
💀 [CRITICAL] ROOT_SHELL_SPAWN
   Root shell spawned: 'bash' (PID 1001)
```

**Demo time:** ~2 seconds

---

### **Scenario 8: 🟡 RAPID_CONNECTIONS Attack**
**Real-world Example:** Network port scanning, worm propagation, botnet spreading

**What it does:**
- Simulates 50 rapid connection attempts
- Shows scanning of `192.168.1.0/24` network on port 445 (SMB)

**Expected CyberCBP Alert:**
```
🟡 [MEDIUM] RAPID_CONNECTIONS
   Rapid connection burst: 50 new connections in one monitoring interval
```

**Demo time:** ~2 seconds

---

### **Scenario 9: 🎯 MULTI_STAGE_ATTACK (Full Attack Chain)**
**Real-world Example:** Sophisticated APT (Advanced Persistent Threat)

**What it does:**
Realistic 4-stage attack chain:

1. **Stage 1 - Reconnaissance (5 sec)**
   - Network scanning with nmap
   - Port detection on SMB (445)
   - **Alert:** 🟡 RAPID_CONNECTIONS

2. **Stage 2 - Exploitation (5 sec)**
   - CPU-intensive brute force (Hydra SSH password cracking)
   - **Alert:** 🟡 HIGH_CPU

3. **Stage 3 - Privilege Escalation (5 sec)**
   - Root shell successfully spawned
   - **Alert:** 💀 ROOT_SHELL_SPAWN

4. **Stage 4 - Exfiltration (5 sec)**
   - Data theft via suspicious port (4444)
   - C2 communication to blacklisted IP
   - **Alerts:** 🔴 SUSPICIOUS_PORT, 🔴 BLACKLISTED_IP

**Total Alerts Generated:** 6 alerts
**Demo time:** ~20 seconds

---

## 🔍 How to Watch for Alerts

### Option 1: Console Output (easiest)
Terminal 1 running CyberCBP will display colored alert panels:

```
╭────────────────────────────────────────────────╮
│ 🟡  [MEDIUM]  HIGH_CPU                         │
│    Process 'mining-bot' (PID 9999) is using... │
│    Source: rules_engine  •  14:23:45           │
╰────────────────────────────────────────────────╯
```

### Option 2: Database Query
In a third terminal:
```bash
sqlite3 db/cybercbp.db "SELECT rule_id, severity, description FROM threats ORDER BY id DESC LIMIT 10;"
```

### Option 3: Dashboard (if running)
```bash
# In a separate terminal, navigate to http://localhost:5000
# (Requires dashboard to be enabled in main.py)
```

### Option 4: Logs
```bash
tail -f cybercbp.log | grep -i "threat\|alert"
```

---

## 📊 Expected Output Example

When you run **Scenario 9 (Multi-Stage Attack)**, you should see in the demo terminal:

```
======================================================================
  Scenario: Full Attack Chain (Reconnaissance + Exploitation + Exfiltration)
======================================================================

→ [Stage 1/4] RECONNAISSANCE - Network scanning...
🚨 DETECTED: RAPID_CONNECTIONS
→ [Stage 2/4] EXPLOITATION - CPU-intensive brute force...
🚨 DETECTED: HIGH_CPU
→ [Stage 3/4] PRIVILEGE ESCALATION - Root shell spawned...
🚨 DETECTED: ROOT_SHELL_SPAWN
→ [Stage 4/4] EXFILTRATION - Data theft + C2 communication...
🚨 DETECTED: SUSPICIOUS_PORT
🚨 DETECTED: BLACKLISTED_IP

✅ Multi-stage attack simulation complete!
⚠️  Check CyberCBP console for ALL alerts (total 6)
```

And in **Terminal 1 (CyberCBP)**, you'll see 6 alert panels appearing in real-time.

---

## ✅ Success Criteria

**The system is working correctly if:**

| Scenario | Expected Alert | Status |
|----------|---|---|
| CPU Attack | 🟡 HIGH_CPU | ✅ Within 5 sec |
| Memory Attack | 🟡 HIGH_MEMORY | ✅ Within 5 sec |
| Suspicious Port | 🔴 SUSPICIOUS_PORT | ✅ Within 2 sec |
| Blacklisted IP | 🔴 BLACKLISTED_IP | ✅ Within 2 sec |
| File Write | 🔴 SENSITIVE_FILE_WRITE | ✅ Within 2 sec |
| File Delete | 💀 SENSITIVE_FILE_DELETE | ✅ Within 2 sec |
| Root Shell | 💀 ROOT_SHELL_SPAWN | ✅ Within 2 sec |
| Rapid Conns | 🟡 RAPID_CONNECTIONS | ✅ Within 2 sec |
| Multi-Stage | All 6 alerts | ✅ Within 20 sec |

---

## 🛠️ Troubleshooting

### Issue: No alerts appearing in Terminal 1

**Possible causes:**
1. CyberCBP not running
   - Check Terminal 1 is actively monitoring
   - Look for "RulesEngine started" message

2. Demo script failed silently
   - Check for error messages in Terminal 2
   - Restart demo with `python3 demo_suspicious_activity.py`

3. Rate limiting (60s cooldown)
   - If you run the same scenario twice, alerts may be suppressed
   - Wait 60 seconds or run a different scenario

**Solution:**
```bash
# Stop CyberCBP (Ctrl+C)
# Clear the database
rm db/cybercbp.db
# Restart
python3 main.py
```

### Issue: Demo terminates unexpectedly

**Solution:**
```bash
# Check for errors in the log
tail -50 cybercbp.log

# Restart with verbose output
python3 -u demo_suspicious_activity.py 2>&1 | tee demo_output.log
```

---

## 📈 Real-World Validation

After running demos, validate detection accuracy:

```bash
# Count total alerts generated
sqlite3 db/cybercbp.db "SELECT COUNT(*) FROM threats;"

# Break down by rule type
sqlite3 db/cybercbp.db "SELECT rule_id, COUNT(*) FROM threats GROUP BY rule_id;"

# Check severity distribution
sqlite3 db/cybercbp.db "SELECT severity, COUNT(*) FROM threats GROUP BY severity;"
```

**Expected for Multi-Stage Attack:**
- Total alerts: 6 (minimum)
- HIGH severity: 2 (SUSPICIOUS_PORT, BLACKLISTED_IP)
- CRITICAL severity: 1 (ROOT_SHELL_SPAWN)
- MEDIUM severity: 3 (RAPID_CONNECTIONS, HIGH_CPU, HIGH_MEMORY)

---

## 🎬 Demo Presentation Script

**If presenting to stakeholders:**

1. **Start CyberCBP** (Terminal 1)
   - Show the system is actively monitoring
   - Highlight "RulesEngine started", "AlertManager started"

2. **Run Demo** (Terminal 2)
   - Explain what each attack scenario simulates
   - Select Scenario 9 (Multi-Stage Attack) for maximum impact

3. **Watch Alerts** (Terminal 1)
   - Point out colored alert panels appearing
   - Highlight severity levels (🟡 MEDIUM → 💀 CRITICAL)
   - Show rule IDs and descriptions

4. **Query Results**
   ```bash
   sqlite3 db/cybercbp.db "SELECT rule_id, severity, description FROM threats ORDER BY id DESC LIMIT 6;"
   ```

5. **Conclusion**
   - "CyberCBP detected **6 distinct attack stages** in real-time"
   - "Each alert was triggered within 2 seconds of detection"
   - "System is ready for production deployment"

---

## 🔐 Safety Notes

✅ **Safe to run:**
- All simulations are synthetic (no real malware/attacks)
- No actual system files modified
- No real network traffic outside localhost
- No real processes terminated
- Can be run repeatedly without damage

---

## 📚 Documentation Files

- `demo_suspicious_activity.py` — Interactive simulator
- `SAFE_TESTING_GUIDE.md` — Safe testing procedures
- `TESTING_REFERENCE.md` — Quick reference
- `quick_test.sh` — Automated unit tests

---

**Ready to demonstrate your threat detection system! 🛡️**
