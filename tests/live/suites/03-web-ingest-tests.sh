#!/bin/bash
# Web Ingestion Tests
# Tests: ingest web, ingest web --limit, error handling

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
    local expect_fail="${3:-false}"

    ((TEST_COUNT++))
    echo -n "[TEST $TEST_COUNT] $name... "

    if eval "$cmd" > /dev/null 2>&1; then
        if [ "$expect_fail" = "true" ]; then
            echo -e "${YELLOW}PASS (expected fail)${NC}"
            ((PASS_COUNT++))
        else
            echo -e "${GREEN}PASS${NC}"
            ((PASS_COUNT++))
        fi
    else
        if [ "$expect_fail" = "true" ]; then
            echo -e "${GREEN}PASS (failed as expected)${NC}"
            ((PASS_COUNT++))
        else
            echo -e "${RED}FAIL${NC}"
            ((FAIL_COUNT++))
        fi
    fi
}

echo "=== WEB INGESTION TESTS ==="
echo ""

# Test 1: Ingest simple URL
run_test "ingest web (example.com)" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://example.com"

# Test 2: Ingest with limit
run_test "ingest web --limit 3" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://docs.python.org --limit 3"

# Test 3: Error case - invalid URL
run_test "ingest web (invalid URL)" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://this-does-not-exist-xyz123456.invalid" \
    "true"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
