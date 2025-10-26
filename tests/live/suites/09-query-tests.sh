#!/bin/bash
# Retrieval & Query Tests
# Tests: query command with various options

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

echo "=== RETRIEVAL & QUERY TESTS ==="
echo ""

# Test 1: Basic query
run_test "query (basic)" \
    "uv run python -m apps.cli.taboot_cli.main query 'what services are running?'"

# Test 2: Query with source filter
run_test "query --sources web" \
    "uv run python -m apps.cli.taboot_cli.main query 'configuration' --sources web"

# Test 3: Query with top-k limit
run_test "query --top-k 5" \
    "uv run python -m apps.cli.taboot_cli.main query 'explain docker compose' --top-k 5"

# Test 4: Query with multiple sources
run_test "query --sources web,github" \
    "uv run python -m apps.cli.taboot_cli.main query 'recent changes' --sources web,github"

# Test 5: Query with date filter
run_test "query --after 2025-01-01" \
    "uv run python -m apps.cli.taboot_cli.main query 'recent updates' --after 2025-01-01"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
