#!/bin/bash
# run_all_demos.sh — Automated Demo Runner
# 
# Runs all 9 attack scenarios sequentially with pauses for observation
# Perfect for automated demonstration/validation

set -e

BASE_DIR="/Users/nihaldastagiri/Desktop/Cyber CBP"
cd "$BASE_DIR"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "\n${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}\n"
}

print_scenario() {
    echo -e "${BOLD}${YELLOW}[Demo $1] $2${NC}"
    echo -e "${BLUE}→ Expected Alert: $3${NC}\n"
}

print_waiting() {
    echo -e "${MAGENTA}⏳ Waiting for alert... ($1s)${NC}"
    sleep "$1"
}

print_complete() {
    echo -e "${GREEN}✅ Scenario complete${NC}\n"
}

main() {
    print_header "🎯 CyberCBP — Automated Demo Runner"
    
    echo -e "${BOLD}This script runs all 9 attack scenarios sequentially.${NC}"
    echo -e "${BOLD}Make sure CyberCBP is running in another terminal!${NC}\n"
    
    read -p "Press Enter to start..." -r
    
    # Verify CyberCBP is running
    if ! pgrep -f "python3 main.py" > /dev/null 2>&1; then
        echo -e "${RED}❌ ERROR: CyberCBP not running!${NC}"
        echo -e "${RED}Start it first: python3 main.py${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ CyberCBP detected running${NC}\n"
    
    # Scenario 1: HIGH_CPU
    print_scenario "1/9" "HIGH_CPU Attack (Crypto Mining)" "🟡 HIGH_CPU"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=65.0, memory_percent=45.0,
    processes=[{"pid": 9999, "name": "mining-bot", "cpu_percent": 87.5,
               "memory_percent": 5.0, "username": "attacker", 
               "cmdline": "mining-bot --threads 4"}],
    connections=[], listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ HIGH_CPU snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 2: HIGH_MEMORY
    print_scenario "2/9" "HIGH_MEMORY Attack (Memory Bomb)" "🟡 HIGH_MEMORY"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=15.0, memory_percent=91.5, memory_available_mb=256.0,
    processes=[{"pid": 8888, "name": "memory-bomb", "cpu_percent": 2.0,
               "memory_percent": 45.0, "username": "attacker", 
               "cmdline": "memory-bomb --size 500MB"}],
    connections=[], listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ HIGH_MEMORY snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 3: SUSPICIOUS_PORT
    print_scenario "3/9" "SUSPICIOUS_PORT Attack (Botnet C2)" "🔴 SUSPICIOUS_PORT"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=8.0, memory_percent=50.0,
    processes=[{"pid": 5555, "name": "trojan", "cpu_percent": 1.5,
               "memory_percent": 3.0, "username": "attacker", 
               "cmdline": "trojan --beacon 10.10.10.10:4444"}],
    connections=[{"laddr": "192.168.1.100:52341", "raddr": "198.51.100.45:4444",
                 "status": "ESTABLISHED", "pid": 5555}],
    listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ SUSPICIOUS_PORT snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 4: BLACKLISTED_IP
    print_scenario "4/9" "BLACKLISTED_IP Attack (Exfiltration)" "🔴 BLACKLISTED_IP"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot
from threat_intel.intel_manager import IntelManager

intel = IntelManager()
with intel._lock:
    intel._bad_ips.add("203.0.113.50")

snap = SystemSnapshot(
    cpu_percent=5.0, memory_percent=48.0,
    processes=[{"pid": 7777, "name": "malware", "cpu_percent": 0.5,
               "memory_percent": 2.0, "username": "attacker", 
               "cmdline": "malware --exfiltrate"}],
    connections=[{"laddr": "192.168.1.100:54321", "raddr": "203.0.113.50:443",
                 "status": "ESTABLISHED", "pid": 7777}],
    listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ BLACKLISTED_IP snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 5: FILE_WRITE
    print_scenario "5/9" "SENSITIVE_FILE_WRITE (File Tampering)" "🔴 SENSITIVE_FILE_WRITE"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=3.0, memory_percent=40.0,
    processes=[{"pid": 6666, "name": "exploit", "cpu_percent": 0.1,
               "memory_percent": 1.0, "username": "attacker", 
               "cmdline": "exploit --target /etc/sudoers"}],
    connections=[], listening_ports=[],
    file_events=[
        {"type": "modify", "src": "/etc/hosts", "dest": ""},
        {"type": "create", "src": "/etc/ssh/authorized_keys", "dest": ""},
        {"type": "modify", "src": "/bin/ls", "dest": ""},
    ]
)
safe_put(event_queue, snap)
print("✓ SENSITIVE_FILE_WRITE snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 6: FILE_DELETE
    print_scenario "6/9" "SENSITIVE_FILE_DELETE (Ransomware)" "💀 SENSITIVE_FILE_DELETE"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=2.0, memory_percent=35.0,
    processes=[{"pid": 4444, "name": "ransomware", "cpu_percent": 0.2,
               "memory_percent": 0.5, "username": "root", 
               "cmdline": "ransomware --encrypt all"}],
    connections=[], listening_ports=[],
    file_events=[
        {"type": "delete", "src": "/etc/passwd", "dest": ""},
        {"type": "delete", "src": "/etc/shadow", "dest": ""},
        {"type": "delete", "src": "/bin/sh", "dest": ""},
    ]
)
safe_put(event_queue, snap)
print("✓ SENSITIVE_FILE_DELETE snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 7: ROOT_SHELL
    print_scenario "7/9" "ROOT_SHELL_SPAWN (Privilege Escalation)" "💀 ROOT_SHELL_SPAWN"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=4.0, memory_percent=42.0,
    processes=[
        {"pid": 1000, "name": "exploit", "cpu_percent": 5.0,
         "memory_percent": 2.0, "username": "attacker", 
         "cmdline": "exploit --privilege-escalation"},
        {"pid": 1001, "name": "bash", "cpu_percent": 0.1,
         "memory_percent": 1.0, "username": "root", 
         "cmdline": "bash -i"}
    ],
    connections=[], listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ ROOT_SHELL_SPAWN snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 8: RAPID_CONNECTIONS
    print_scenario "8/9" "RAPID_CONNECTIONS (Port Scanning)" "🟡 RAPID_CONNECTIONS"
    python3 << 'PYSCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot

snap = SystemSnapshot(
    cpu_percent=25.0, memory_percent=55.0,
    processes=[{"pid": 3333, "name": "worm", "cpu_percent": 15.0,
               "memory_percent": 5.0, "username": "attacker", 
               "cmdline": "worm --scan-network 192.168.1.0/24"}],
    connections=[
        {"laddr": f"192.168.1.100:{50000+i}", "raddr": f"192.168.1.{100+i}:445",
         "status": "SYN_SENT", "pid": 3333}
        for i in range(50)
    ],
    listening_ports=[], num_new_connections=50
)
safe_put(event_queue, snap)
print("✓ RAPID_CONNECTIONS snapshot injected")
PYSCRIPT
    print_waiting "5"
    print_complete
    
    # Scenario 9: MULTI_STAGE
    print_scenario "9/9" "MULTI_STAGE_ATTACK (Full Attack Chain)" "🎯 6 Total Alerts"
    python3 << 'PYSCRIPT'
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.event_queue import event_queue, safe_put
from core.threat_event import SystemSnapshot
from threat_intel.intel_manager import IntelManager

# Stage 1
snap = SystemSnapshot(
    cpu_percent=20.0, memory_percent=50.0,
    processes=[{"pid": 2000, "name": "nmap", "cpu_percent": 10.0, "memory_percent": 3.0, "username": "attacker", "cmdline": "nmap -sV 192.168.1.0/24"}],
    connections=[{"laddr": f"192.168.1.100:{50000+i}", "raddr": f"192.168.1.{100+i}:445", "status": "SYN_SENT", "pid": 2000} for i in range(30)],
    listening_ports=[], num_new_connections=30
)
safe_put(event_queue, snap)
print("✓ Stage 1: Reconnaissance")
time.sleep(3)

# Stage 2
snap = SystemSnapshot(
    cpu_percent=85.0, memory_percent=65.0,
    processes=[{"pid": 2001, "name": "hydra", "cpu_percent": 92.0, "memory_percent": 8.0, "username": "attacker", "cmdline": "hydra -l admin -P passwords.txt ssh://192.168.1.50"}],
    connections=[], listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ Stage 2: Exploitation")
time.sleep(3)

# Stage 3
snap = SystemSnapshot(
    cpu_percent=5.0, memory_percent=48.0,
    processes=[{"pid": 2002, "name": "bash", "cpu_percent": 0.1, "memory_percent": 1.0, "username": "root", "cmdline": "bash -i"}],
    connections=[], listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ Stage 3: Privilege Escalation")
time.sleep(3)

# Stage 4
intel = IntelManager()
with intel._lock:
    intel._bad_ips.add("203.0.113.50")

snap = SystemSnapshot(
    cpu_percent=15.0, memory_percent=60.0,
    processes=[{"pid": 2003, "name": "data-exfil", "cpu_percent": 8.0, "memory_percent": 15.0, "username": "root", "cmdline": "data-exfil --target attacker.com"}],
    connections=[
        {"laddr": "192.168.1.100:54321", "raddr": "198.51.100.45:4444", "status": "ESTABLISHED", "pid": 2003},
        {"laddr": "192.168.1.100:54322", "raddr": "203.0.113.50:443", "status": "ESTABLISHED", "pid": 2003}
    ],
    listening_ports=[]
)
safe_put(event_queue, snap)
print("✓ Stage 4: Exfiltration")
PYSCRIPT
    print_waiting "10"
    print_complete
    
    print_header "🎉 All Scenarios Complete!"
    
    echo -e "${GREEN}✅ All 9 attack scenarios have been simulated${NC}"
    echo -e "${GREEN}✅ Check CyberCBP console for all alerts${NC}\n"
    
    echo -e "${BOLD}Verify results:${NC}"
    echo -e "${CYAN}  sqlite3 db/cybercbp.db \"SELECT rule_id, COUNT(*) FROM threats GROUP BY rule_id;\"${NC}\n"
    
    echo -e "${BOLD}Expected detections:${NC}"
    echo -e "  • HIGH_CPU (1-2)"
    echo -e "  • HIGH_MEMORY (1)"
    echo -e "  • SUSPICIOUS_PORT (2)"
    echo -e "  • BLACKLISTED_IP (1)"
    echo -e "  • SENSITIVE_FILE_WRITE (1)"
    echo -e "  • SENSITIVE_FILE_DELETE (1)"
    echo -e "  • ROOT_SHELL_SPAWN (1)"
    echo -e "  • RAPID_CONNECTIONS (2)\n"
}

main "$@"
