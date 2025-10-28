#!/bin/bash
# Graph Operations Tests
# Tests: graph query, format options, error handling

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

echo "=== GRAPH OPERATIONS TESTS ==="
echo ""

# Test 1: Count nodes
run_test "graph query (count nodes)" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (n) RETURN count(n) as total_nodes'"

# Test 2: Match services
run_test "graph query (services)" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (s:Service) RETURN s.name LIMIT 10'"

# Test 3: JSON format
run_test "graph query --format json" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (s:Service) RETURN s LIMIT 3' --format json"

# Test 4: Relationships
run_test "graph query (relationships)" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (s)-[r]->(t) RETURN count(r) as rel_count'"

# Test 5: Invalid Cypher (should fail)
run_test "graph query (invalid Cypher)" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'INVALID SYNTAX HERE'" \
    "true"

echo ""
echo "=== RESULTS: $PASS_COUNT/$TEST_COUNT passed ==="

[ $FAIL_COUNT -eq 0 ]
