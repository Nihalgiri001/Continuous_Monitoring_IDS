#!/bin/bash
# quick_test.sh — Run all safety tests with one command

set -e

BASE_DIR="/Users/nihaldastagiri/Desktop/Cyber CBP"
cd "$BASE_DIR"

echo "🔒 CyberCBP — Safe Intrusion Testing Suite"
echo "==========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

run_test() {
    local test_name=$1
    local test_file=$2
    echo -e "${YELLOW}🧪 Running: $test_name${NC}"
    echo "   File: $test_file"
    if python3 "$test_file"; then
        echo -e "${GREEN}   ✅ PASSED${NC}\n"
        return 0
    else
        echo -e "${RED}   ❌ FAILED${NC}\n"
        return 1
    fi
}

# Track results
passed=0
total=0

# Test 1: High CPU/Memory
total=$((total + 1))
if run_test "HIGH_CPU / HIGH_MEMORY Detection" "tests/test_high_cpu.py"; then
    passed=$((passed + 1))
fi

# Test 2: File Modifications
total=$((total + 1))
if run_test "SENSITIVE_FILE_WRITE / DELETE Detection" "tests/test_file_modification.py"; then
    passed=$((passed + 1))
fi

# Test 3: Suspicious Ports
total=$((total + 1))
if run_test "SUSPICIOUS_PORT / BLACKLISTED_IP Detection" "tests/test_suspicious_port.py"; then
    passed=$((passed + 1))
fi

# Summary
echo "==========================================="
echo -e "${GREEN}Results: $passed/$total tests passed${NC}"

if [ "$passed" -eq "$total" ]; then
    echo -e "${GREEN}✅ All tests passed! System is ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review above for details.${NC}"
    exit 1
fi
