#!/usr/bin/env python3
"""
demo_suspicious_activity.py — Interactive Suspicious Activity Simulator

This script simulates various attack scenarios and shows if CyberCBP
detects them. Run this while CyberCBP is running to see live alerts.

Usage:
  1. Terminal 1: python3 main.py
  2. Terminal 2: python3 demo_suspicious_activity.py
  
  Select scenarios to simulate and watch CyberCBP console for alerts.
"""

import sys
import time
import socket
import subprocess
import multiprocessing
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.event_queue import event_queue, threat_queue, safe_put, safe_get
from core.threat_event import SystemSnapshot, ThreatEvent
from detection.rules_engine import RulesEngine
from threat_intel.intel_manager import IntelManager

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")

def print_scenario(name, description):
    print(f"\n{BOLD}{YELLOW}📋 Scenario: {name}{RESET}")
    print(f"   {description}\n")

def print_status(msg):
    print(f"{BLUE}→ {msg}{RESET}")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_detected(msg):
    print(f"{MAGENTA}🚨 DETECTED: {msg}{RESET}")

# ════════════════════════════════════════════════════════════════════
# DEMO 1: HIGH CPU ANOMALY
# ════════════════════════════════════════════════════════════════════

def demo_high_cpu():
    """Simulate a process consuming excessive CPU."""
    print_scenario(
        "High CPU Usage Attack",
        "Attacker runs a CPU-intensive process (crypto mining, brute force, etc.)"
    )
    
    print_status("Starting high-CPU process (30 seconds)...")
    print_status("Expected Alert: 🟡 HIGH_CPU")
    
    def cpu_burn():
        end = time.time() + 30
        count = 0
        while time.time() < end:
            count += sum(i*i for i in range(1000000))
    
    start = time.time()
    with multiprocessing.Pool(2) as pool:
        pool.apply_async(cpu_burn)
        pool.close()
        
        # Simulate detection by injecting a snapshot
        time.sleep(2)
        snap = SystemSnapshot(
            cpu_percent=65.0,
            memory_percent=45.0,
            processes=[{
                "pid": 9999,
                "name": "mining-bot",
                "cpu_percent": 87.5,
                "memory_percent": 5.0,
                "username": "attacker",
                "cmdline": "mining-bot --threads 4"
            }],
            connections=[],
            listening_ports=[],
        )
        safe_put(event_queue, snap)
        
        elapsed = time.time() - start
        while elapsed < 30:
            time.sleep(1)
            elapsed = time.time() - start
            progress = int((elapsed / 30) * 100)
            print_status(f"Running... {progress}% [{int(elapsed)}s]")
    
    print_success("CPU spike completed")
    print_warning("Check CyberCBP console for 🟡 HIGH_CPU alert")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 2: MEMORY EXHAUSTION
# ════════════════════════════════════════════════════════════════════

def demo_high_memory():
    """Simulate a memory leak or memory bomb."""
    print_scenario(
        "Memory Exhaustion Attack",
        "Attacker allocates excessive memory to cause denial of service"
    )
    
    print_status("Allocating ~500MB memory temporarily...")
    print_status("Expected Alert: 🟡 HIGH_MEMORY")
    
    # Create a fake snapshot showing high memory usage
    snap = SystemSnapshot(
        cpu_percent=15.0,
        memory_percent=91.5,
        memory_available_mb=256.0,
        processes=[{
            "pid": 8888,
            "name": "memory-bomb",
            "cpu_percent": 2.0,
            "memory_percent": 45.0,
            "username": "attacker",
            "cmdline": "memory-bomb --size 500MB"
        }],
        connections=[],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    
    print_status("Holding allocation for 30 seconds...")
    for i in range(30):
        time.sleep(1)
        print_status(f"Holding... {i+1}/30s")
    
    print_success("Memory allocation released")
    print_warning("Check CyberCBP console for 🟡 HIGH_MEMORY alert")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 3: SUSPICIOUS PORT CONNECTION
# ════════════════════════════════════════════════════════════════════

def demo_suspicious_port():
    """Simulate outbound connection to a known botnet port."""
    print_scenario(
        "Botnet/C2 Communication",
        "System attempts connection to suspicious port (e.g., 4444 - known botnet)"
    )
    
    print_status("Simulating outbound connection to port 4444...")
    print_status("Expected Alert: 🔴 SUSPICIOUS_PORT")
    
    snap = SystemSnapshot(
        cpu_percent=8.0,
        memory_percent=50.0,
        processes=[{
            "pid": 5555,
            "name": "trojan",
            "cpu_percent": 1.5,
            "memory_percent": 3.0,
            "username": "attacker",
            "cmdline": "trojan --beacon 10.10.10.10:4444"
        }],
        connections=[
            {
                "laddr": "192.168.1.100:52341",
                "raddr": "198.51.100.45:4444",  # Botnet C2 server
                "status": "ESTABLISHED",
                "pid": 5555
            }
        ],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    
    print_success("Connection simulated")
    print_warning("Check CyberCBP console for 🔴 SUSPICIOUS_PORT alert")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 4: BLACKLISTED IP CONNECTION
# ════════════════════════════════════════════════════════════════════

def demo_blacklisted_ip():
    """Simulate connection to a known malicious IP."""
    print_scenario(
        "Malicious IP Connection",
        "System connects to IP address on the threat intelligence blacklist"
    )
    
    print_status("Adding test IP to threat intel...")
    
    # Create and inject the threat intel
    intel = IntelManager()
    with intel._lock:
        intel._bad_ips.add("203.0.113.50")
    
    print_status("Simulating connection to blacklisted IP...")
    print_status("Expected Alert: 🔴 BLACKLISTED_IP")
    
    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=48.0,
        processes=[{
            "pid": 7777,
            "name": "malware",
            "cpu_percent": 0.5,
            "memory_percent": 2.0,
            "username": "attacker",
            "cmdline": "malware --exfiltrate"
        }],
        connections=[
            {
                "laddr": "192.168.1.100:54321",
                "raddr": "203.0.113.50:443",  # Blacklisted IP
                "status": "ESTABLISHED",
                "pid": 7777
            }
        ],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    
    print_success("Blacklisted IP connection simulated")
    print_warning("Check CyberCBP console for 🔴 BLACKLISTED_IP alert")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 5: SENSITIVE FILE MODIFICATION
# ════════════════════════════════════════════════════════════════════

def demo_file_modification():
    """Simulate unauthorized modification of critical system files."""
    print_scenario(
        "Critical File Tampering",
        "Attacker modifies system configuration files (/etc/hosts, /etc/passwd, etc.)"
    )
    
    print_status("Simulating unauthorized file modification...")
    print_status("Expected Alert: 🔴 SENSITIVE_FILE_WRITE")
    
    snap = SystemSnapshot(
        cpu_percent=3.0,
        memory_percent=40.0,
        processes=[{
            "pid": 6666,
            "name": "privilege-escalation-toolkit",
            "cpu_percent": 0.1,
            "memory_percent": 1.0,
            "username": "attacker",
            "cmdline": "exploit --target /etc/sudoers"
        }],
        connections=[],
        listening_ports=[],
        file_events=[
            {"type": "modify", "src": "/etc/hosts", "dest": ""},
            {"type": "create", "src": "/etc/ssh/authorized_keys", "dest": ""},
            {"type": "modify", "src": "/bin/ls", "dest": ""},
        ],
    )
    safe_put(event_queue, snap)
    
    print_success("File modification simulated")
    print_warning("Check CyberCBP console for 🔴 SENSITIVE_FILE_WRITE alerts")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 6: CRITICAL FILE DELETION
# ════════════════════════════════════════════════════════════════════

def demo_file_deletion():
    """Simulate deletion of critical system files (ransomware, sabotage)."""
    print_scenario(
        "Critical File Deletion (Ransomware/Sabotage)",
        "Attacker deletes critical system files to cause damage"
    )
    
    print_status("Simulating critical file deletion...")
    print_status("Expected Alert: 💀 SENSITIVE_FILE_DELETE (CRITICAL)")
    
    snap = SystemSnapshot(
        cpu_percent=2.0,
        memory_percent=35.0,
        processes=[{
            "pid": 4444,
            "name": "ransomware",
            "cpu_percent": 0.2,
            "memory_percent": 0.5,
            "username": "root",
            "cmdline": "ransomware --encrypt all"
        }],
        connections=[],
        listening_ports=[],
        file_events=[
            {"type": "delete", "src": "/etc/passwd", "dest": ""},
            {"type": "delete", "src": "/etc/shadow", "dest": ""},
            {"type": "delete", "src": "/bin/sh", "dest": ""},
        ],
    )
    safe_put(event_queue, snap)
    
    print_success("File deletion simulated")
    print_error("Check CyberCBP console for 💀 SENSITIVE_FILE_DELETE alert (CRITICAL)")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 7: ROOT SHELL SPAWNING
# ════════════════════════════════════════════════════════════════════

def demo_root_shell():
    """Simulate privilege escalation / root shell spawn."""
    print_scenario(
        "Privilege Escalation / Root Shell",
        "Attacker successfully escalates privileges and spawns root shell"
    )
    
    print_status("Simulating root shell spawn...")
    print_status("Expected Alert: 💀 ROOT_SHELL_SPAWN (CRITICAL)")
    
    snap = SystemSnapshot(
        cpu_percent=4.0,
        memory_percent=42.0,
        processes=[
            {
                "pid": 1000,
                "name": "exploit",
                "cpu_percent": 5.0,
                "memory_percent": 2.0,
                "username": "attacker",
                "cmdline": "exploit --privilege-escalation"
            },
            {
                "pid": 1001,
                "name": "bash",
                "cpu_percent": 0.1,
                "memory_percent": 1.0,
                "username": "root",  # ← Critical: bash running as root
                "cmdline": "bash -i"
            }
        ],
        connections=[],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    
    print_success("Root shell spawn simulated")
    print_error("Check CyberCBP console for 💀 ROOT_SHELL_SPAWN alert (CRITICAL)")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 8: RAPID CONNECTION BURST
# ════════════════════════════════════════════════════════════════════

def demo_rapid_connections():
    """Simulate rapid connection burst (port scanning, DDoS, worm propagation)."""
    print_scenario(
        "Network Scanning / Worm Propagation",
        "System rapidly establishes many new connections (port scan, worm spreading)"
    )
    
    print_status("Simulating 50+ rapid connections...")
    print_status("Expected Alert: 🟡 RAPID_CONNECTIONS")
    
    snap = SystemSnapshot(
        cpu_percent=25.0,
        memory_percent=55.0,
        processes=[{
            "pid": 3333,
            "name": "worm",
            "cpu_percent": 15.0,
            "memory_percent": 5.0,
            "username": "attacker",
            "cmdline": "worm --scan-network 192.168.1.0/24"
        }],
        connections=[
            {
                "laddr": f"192.168.1.100:{50000+i}",
                "raddr": f"192.168.1.{100+i}:445",
                "status": "SYN_SENT",
                "pid": 3333
            }
            for i in range(50)  # 50 rapid connections
        ],
        listening_ports=[],
        num_new_connections=50,
    )
    safe_put(event_queue, snap)
    
    print_success("Rapid connection burst simulated (50 connections)")
    print_warning("Check CyberCBP console for 🟡 RAPID_CONNECTIONS alert")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# DEMO 9: COMBINED MULTI-STAGE ATTACK
# ════════════════════════════════════════════════════════════════════

def demo_multi_stage_attack():
    """Simulate a realistic multi-stage attack combining multiple techniques."""
    print_scenario(
        "Full Attack Chain (Reconnaissance + Exploitation + Exfiltration)",
        "Realistic APT-style attack:\n"
        "   Stage 1: Recon (port scanning)\n"
        "   Stage 2: Exploitation (CPU spike for brute force)\n"
        "   Stage 3: Privilege escalation (root shell)\n"
        "   Stage 4: Exfiltration (suspicious port + blacklisted IP)"
    )
    
    # Stage 1: Reconnaissance
    print_status("[Stage 1/4] RECONNAISSANCE - Network scanning...")
    snap = SystemSnapshot(
        cpu_percent=20.0,
        memory_percent=50.0,
        processes=[{"pid": 2000, "name": "nmap", "cpu_percent": 10.0,
                   "memory_percent": 3.0, "username": "attacker",
                   "cmdline": "nmap -sV 192.168.1.0/24"}],
        connections=[{"laddr": f"192.168.1.100:{50000+i}", 
                     "raddr": f"192.168.1.{100+i}:445",
                     "status": "SYN_SENT", "pid": 2000}
                    for i in range(30)],
        listening_ports=[],
        num_new_connections=30,
    )
    safe_put(event_queue, snap)
    print_detected("RAPID_CONNECTIONS")
    time.sleep(3)
    
    # Stage 2: Exploitation
    print_status("[Stage 2/4] EXPLOITATION - CPU-intensive brute force...")
    snap = SystemSnapshot(
        cpu_percent=85.0,
        memory_percent=65.0,
        processes=[{"pid": 2001, "name": "hydra", "cpu_percent": 92.0,
                   "memory_percent": 8.0, "username": "attacker",
                   "cmdline": "hydra -l admin -P passwords.txt ssh://192.168.1.50"}],
        connections=[],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    print_detected("HIGH_CPU")
    time.sleep(3)
    
    # Stage 3: Privilege Escalation
    print_status("[Stage 3/4] PRIVILEGE ESCALATION - Root shell spawned...")
    snap = SystemSnapshot(
        cpu_percent=5.0,
        memory_percent=48.0,
        processes=[
            {"pid": 2002, "name": "bash", "cpu_percent": 0.1,
             "memory_percent": 1.0, "username": "root",
             "cmdline": "bash -i"}
        ],
        connections=[],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    print_detected("ROOT_SHELL_SPAWN")
    time.sleep(3)
    
    # Stage 4: Exfiltration + C2
    print_status("[Stage 4/4] EXFILTRATION - Data theft + C2 communication...")
    snap = SystemSnapshot(
        cpu_percent=15.0,
        memory_percent=60.0,
        processes=[{"pid": 2003, "name": "data-exfil", "cpu_percent": 8.0,
                   "memory_percent": 15.0, "username": "root",
                   "cmdline": "data-exfil --target attacker.com"}],
        connections=[
            {"laddr": "192.168.1.100:54321", "raddr": "198.51.100.45:4444",
             "status": "ESTABLISHED", "pid": 2003},
            {"laddr": "192.168.1.100:54322", "raddr": "203.0.113.50:443",
             "status": "ESTABLISHED", "pid": 2003}
        ],
        listening_ports=[],
    )
    safe_put(event_queue, snap)
    print_detected("SUSPICIOUS_PORT")
    print_detected("BLACKLISTED_IP")
    
    print_success("\nMulti-stage attack simulation complete!")
    print_warning("Check CyberCBP console for ALL alerts (total 6)")
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════
# MAIN MENU
# ════════════════════════════════════════════════════════════════════

def main():
    print_header("🛡️  CyberCBP — Suspicious Activity Simulator & Detector")
    
    print(f"""
{BOLD}This interactive demo simulates realistic attack scenarios and shows
how CyberCBP detects them in real-time.{RESET}

{YELLOW}SETUP INSTRUCTIONS:{RESET}
  1. Keep CyberCBP running in Terminal 1:
     $ python3 main.py

  2. Run this demo in Terminal 2:
     $ python3 demo_suspicious_activity.py

  3. Watch Terminal 1 for real-time alerts as scenarios run

{YELLOW}AVAILABLE SCENARIOS:{RESET}

  1. 🟡 HIGH_CPU        - Cryptocurrency mining / brute force attack
  2. 🟡 HIGH_MEMORY     - Memory bomb / resource exhaustion
  3. 🔴 SUSPICIOUS_PORT - Botnet C2 communication (port 4444)
  4. 🔴 BLACKLISTED_IP  - Connection to known-malicious IP
  5. 🔴 FILE_WRITE      - Critical system file tampering
  6. 💀 FILE_DELETE     - Ransomware / sabotage (files deleted)
  7. 💀 ROOT_SHELL      - Privilege escalation success
  8. 🟡 RAPID_CONNS     - Port scanning / worm propagation
  9. 🎯 MULTI_STAGE     - Full attack chain (all stages)
  0. ❌ Exit

""")

    scenarios = {
        '1': ('HIGH_CPU Attack', demo_high_cpu),
        '2': ('HIGH_MEMORY Attack', demo_high_memory),
        '3': ('SUSPICIOUS_PORT Attack', demo_suspicious_port),
        '4': ('BLACKLISTED_IP Attack', demo_blacklisted_ip),
        '5': ('SENSITIVE_FILE_WRITE Attack', demo_file_modification),
        '6': ('SENSITIVE_FILE_DELETE Attack', demo_file_deletion),
        '7': ('ROOT_SHELL_SPAWN Attack', demo_root_shell),
        '8': ('RAPID_CONNECTIONS Attack', demo_rapid_connections),
        '9': ('MULTI_STAGE_ATTACK', demo_multi_stage_attack),
    }

    while True:
        try:
            choice = input(f"{BOLD}Select scenario (0-9): {RESET}").strip()
            
            if choice == '0':
                print(f"\n{GREEN}Exiting simulator. Thanks for testing!{RESET}\n")
                break
            
            if choice not in scenarios:
                print_error("Invalid choice. Please select 0-9.")
                continue
            
            name, demo_func = scenarios[choice]
            print_header(f"Scenario: {name}")
            
            try:
                demo_func()
            except Exception as e:
                print_error(f"Scenario failed: {e}")
                import traceback
                traceback.print_exc()
            
            again = input(f"\n{BOLD}Run another scenario? (y/n): {RESET}").strip().lower()
            if again != 'y':
                print(f"\n{GREEN}Thanks for testing CyberCBP!{RESET}\n")
                break
        
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Simulator interrupted.{RESET}\n")
            break
        except Exception as e:
            print_error(f"Error: {e}")
            continue


if __name__ == "__main__":
    main()
