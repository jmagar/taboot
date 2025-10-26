#!/bin/bash
# Extraction Pipeline Tests
# Tests: extract pending, extract status, extract reprocess

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0

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
    fi
}

echo "=== EXTRACTION PIPELINE TESTS ==="
echo ""

# Test 1: Extract pending documents
run_test "extract pending (all)" \
    "uv run python -m apps.cli.taboot_cli.main extract pending"

# Test 2: Extract pending with limit
run_test "extract pending --limit 5" \
    "uv run python -m apps.cli.taboot_cli.main extract pending --limit 5"

# Test 3: Check extraction status
run_test "extract status" \
    "uv run python -m apps.cli.taboot_cli.main extract status"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
