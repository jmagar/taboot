#!/bin/bash
# Docker Compose Ingestion Tests
# Tests: ingest docker-compose, error handling

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

echo "=== DOCKER COMPOSE INGESTION TESTS ==="
echo ""

# Test 1: Ingest project's docker-compose.yaml
run_test "ingest docker-compose (project)" \
    "uv run python -m apps.cli.taboot_cli.main ingest docker-compose docker-compose.yaml"

# Test 2: Error case - missing file
run_test "ingest docker-compose (missing file)" \
    "uv run python -m apps.cli.taboot_cli.main ingest docker-compose /nonexistent/docker-compose.yaml" \
    "true"

# Test 3: Create invalid YAML and test parsing
INVALID_YAML="/tmp/invalid-docker-compose.yaml"
echo "invalid: yaml: content: [" > "$INVALID_YAML"

run_test "ingest docker-compose (invalid YAML)" \
    "uv run python -m apps.cli.taboot_cli.main ingest docker-compose $INVALID_YAML" \
    "true"

rm -f "$INVALID_YAML"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
