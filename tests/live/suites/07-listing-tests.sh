#!/bin/bash
# Listing & Discovery Tests
# Tests: list documents, filters, pagination

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

echo "=== LISTING & DISCOVERY TESTS ==="
echo ""

# Test 1: List all documents
run_test "list documents" \
    "uv run python -m apps.cli.taboot_cli.main list documents"

# Test 2: List with custom limit
run_test "list documents --limit 20" \
    "uv run python -m apps.cli.taboot_cli.main list documents --limit 20"

# Test 3: Filter by source type
run_test "list documents --source-type web" \
    "uv run python -m apps.cli.taboot_cli.main list documents --source-type web"

# Test 4: Pagination
run_test "list documents --limit 5 --offset 0" \
    "uv run python -m apps.cli.taboot_cli.main list documents --limit 5 --offset 0"

# Test 5: Filter by extraction state
run_test "list documents --extraction-state pending" \
    "uv run python -m apps.cli.taboot_cli.main list documents --extraction-state pending"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
