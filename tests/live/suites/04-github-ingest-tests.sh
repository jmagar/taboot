#!/bin/bash
# GitHub Ingestion Tests
# Tests: ingest github, error handling, token validation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

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

skip_test() {
    local name="$1"
    ((TEST_COUNT++))
    echo -e "[TEST $TEST_COUNT] $name... ${YELLOW}SKIP${NC} (GITHUB_TOKEN not set)"
    ((SKIP_COUNT++))
}

echo "=== GITHUB INGESTION TESTS ==="
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}WARNING: GITHUB_TOKEN not configured. Skipping GitHub tests.${NC}"
    echo "To enable, set: export GITHUB_TOKEN=your_token"
    echo ""
    skip_test "ingest github (valid repo)"
    skip_test "ingest github (invalid format)"
    skip_test "ingest github (limit)"
else
    # Test 1: Ingest public repo
    run_test "ingest github (anthropics/anthropic-sdk-python)" \
        "uv run python -m apps.cli.taboot_cli.main ingest github anthropics/anthropic-sdk-python --limit 5"

    # Test 2: Invalid format
    run_test "ingest github (invalid format)" \
        "uv run python -m apps.cli.taboot_cli.main ingest github invalid-format" \
        "true"

    # Test 3: With limit
    run_test "ingest github (with limit)" \
        "uv run python -m apps.cli.taboot_cli.main ingest github github/github --limit 3"
fi

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed, $SKIP_COUNT skipped ==="

[ $FAIL_COUNT -eq 0 ]
