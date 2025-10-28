#!/bin/bash
# Schema & Initialization Tests
# Tests: init, schema version, schema history

set -e

# Color setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0

# Helper function
run_test() {
    local name="$1"
    local cmd="$2"

    ((TEST_COUNT++))
    echo -n "[TEST $TEST_COUNT] $name... "

    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAIL_COUNT++))
        eval "$cmd"
    fi
}

echo "=== SCHEMA & INITIALIZATION TESTS ==="
echo ""

# Test 1: Init system
run_test "taboot init" \
    "uv run python -m apps.cli.taboot_cli.main init"

# Test 2: Check schema version
run_test "schema version" \
    "uv run python -m apps.cli.taboot_cli.main schema version"

# Test 3: Check schema history
run_test "schema history" \
    "uv run python -m apps.cli.taboot_cli.main schema history"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
