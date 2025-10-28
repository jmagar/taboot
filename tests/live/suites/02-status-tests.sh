#!/bin/bash
# Status & Health Check Tests
# Tests: status global, status verbose, status component-specific

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

echo "=== STATUS & HEALTH CHECK TESTS ==="
echo ""

# Test 1: Global status
run_test "status (global)" \
    "uv run python -m apps.cli.taboot_cli.main status"

# Test 2: Verbose status
run_test "status --verbose" \
    "uv run python -m apps.cli.taboot_cli.main status --verbose"

# Test 3-8: Component-specific status
for component in neo4j qdrant redis tei ollama firecrawl playwright; do
    run_test "status --component $component" \
        "uv run python -m apps.cli.taboot_cli.main status --component $component"
done

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
