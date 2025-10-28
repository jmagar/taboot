#!/bin/bash
# Taboot CLI Live Test Suite - Main Orchestration Script
# Runs all CLI tests against live services with no mocks

set -o pipefail

# ============================================================================
# Configuration & Globals
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SUITES_DIR="$SCRIPT_DIR/suites"
OUTPUT_DIR="$SCRIPT_DIR/outputs"
TEST_DATA_DIR="$SCRIPT_DIR/test-data"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
SKIPPED=0
TOTAL=0

# Timing
START_TIME=$(date +%s)

# ============================================================================
# Helper Functions
# ============================================================================

# Print header
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Print section
print_section() {
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}▶ $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print test case
print_test() {
    local name="$1"
    local cmd="$2"
    printf "${YELLOW}[TEST]${NC} %-60s" "$name"
}

# Print result
print_pass() {
    echo -e "${GREEN}[PASS]${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC}"
    ((FAILED++))
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC}"
    ((SKIPPED++))
}

# Run test command
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local expect_fail="${3:-false}"
    local log_file="$OUTPUT_DIR/$(echo "$test_name" | sed 's/ /_/g').log"

    ((TOTAL++))
    print_test "$test_name" "$test_cmd"

    # Execute test command and capture output
    if eval "$test_cmd" > "$log_file" 2>&1; then
        if [ "$expect_fail" = "true" ]; then
            print_fail
            echo "  Expected failure but passed"
            echo "  Log: $log_file"
        else
            print_pass
        fi
    else
        if [ "$expect_fail" = "true" ]; then
            print_pass
        else
            print_fail
            echo "  Log: $log_file"
        fi
    fi
    echo ""
}

# Skip test
skip_test() {
    local test_name="$1"
    local reason="$2"

    ((TOTAL++))
    print_test "$test_name"
    print_skip
    echo "  Reason: $reason"
    echo ""
}

# Check prerequisite
check_prereq() {
    local name="$1"
    local cmd="$2"

    if ! eval "$cmd" > /dev/null 2>&1; then
        echo -e "${RED}✗ Prerequisite failed: $name${NC}"
        echo "  Command: $cmd"
        return 1
    fi
    return 0
}

# ============================================================================
# Prerequisite Checks
# ============================================================================

print_header "TABOOT CLI LIVE TEST SUITE"

echo "Test execution started: $(date)"
echo "Output directory: $OUTPUT_DIR"
echo ""

print_section "PREREQUISITE CHECKS"

# Check Docker services
echo -n "Docker services... "
if docker compose ps --format json > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "ERROR: Docker not available. Start with: docker compose up -d"
    exit 1
fi

# Check CLI availability
echo -n "CLI availability... "
if uv run python -m apps.cli.taboot_cli.main --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "ERROR: CLI not available. Run: uv sync"
    exit 1
fi

# Check service health
echo -n "Service health... "
if uv run python -m apps.cli.taboot_cli.main status > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "WARNING: Services may not be healthy. Status: "
    docker compose ps
fi

echo ""

# ============================================================================
# Test Execution
# ============================================================================

print_section "PHASE 0: SCHEMA & INITIALIZATION"

run_test "01-init" \
    "uv run python -m apps.cli.taboot_cli.main init"

run_test "01-schema-version" \
    "uv run python -m apps.cli.taboot_cli.main schema version"

run_test "01-schema-history" \
    "uv run python -m apps.cli.taboot_cli.main schema history"

print_section "PHASE 1: STATUS & HEALTH"

run_test "02-status-global" \
    "uv run python -m apps.cli.taboot_cli.main status"

run_test "02-status-verbose" \
    "uv run python -m apps.cli.taboot_cli.main status --verbose"

run_test "02-status-component-neo4j" \
    "uv run python -m apps.cli.taboot_cli.main status --component neo4j"

run_test "02-status-component-qdrant" \
    "uv run python -m apps.cli.taboot_cli.main status --component qdrant"

run_test "02-status-component-redis" \
    "uv run python -m apps.cli.taboot_cli.main status --component redis"

print_section "PHASE 2: WEB INGESTION"

run_test "03-ingest-web-example" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://example.com"

run_test "03-ingest-web-limited" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://docs.python.org --limit 3"

run_test "03-ingest-web-error-invalid-url" \
    "uv run python -m apps.cli.taboot_cli.main ingest web https://invalid-xyz-123456789.com" \
    "true"

print_section "PHASE 3: GITHUB INGESTION"

# Check if GITHUB_TOKEN is configured
if [ -n "$GITHUB_TOKEN" ]; then
    run_test "04-ingest-github-valid" \
        "uv run python -m apps.cli.taboot_cli.main ingest github anthropics/anthropic-sdk-python --limit 5"

    run_test "04-ingest-github-error-invalid-format" \
        "uv run python -m apps.cli.taboot_cli.main ingest github invalid-format" \
        "true"
else
    skip_test "04-ingest-github-valid" "GITHUB_TOKEN not configured"
    skip_test "04-ingest-github-error-invalid-format" "GITHUB_TOKEN not configured"
fi

print_section "PHASE 4: DOCKER COMPOSE INGESTION"

run_test "05-ingest-docker-compose" \
    "uv run python -m apps.cli.taboot_cli.main ingest docker-compose docker-compose.yaml"

run_test "05-ingest-docker-compose-error-invalid-file" \
    "uv run python -m apps.cli.taboot_cli.main ingest docker-compose /nonexistent/file.yaml" \
    "true"

print_section "PHASE 5: EXTRACTION PIPELINE"

run_test "07-extract-pending" \
    "uv run python -m apps.cli.taboot_cli.main extract pending --limit 5"

run_test "07-extract-status" \
    "uv run python -m apps.cli.taboot_cli.main extract status"

print_section "PHASE 6: LISTING COMMANDS"

run_test "08-list-documents" \
    "uv run python -m apps.cli.taboot_cli.main list documents --limit 10"

run_test "08-list-documents-web" \
    "uv run python -m apps.cli.taboot_cli.main list documents --limit 10 --source-type web"

run_test "08-list-documents-pagination" \
    "uv run python -m apps.cli.taboot_cli.main list documents --limit 5 --offset 0"

print_section "PHASE 7: GRAPH OPERATIONS"

run_test "09-graph-query-count" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (n) RETURN count(n) as total_nodes'"

run_test "09-graph-query-services" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (s:Service) RETURN s.name LIMIT 10'"

run_test "09-graph-query-json" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'MATCH (s:Service) RETURN s LIMIT 3' --format json"

run_test "09-graph-query-error-invalid-cypher" \
    "uv run python -m apps.cli.taboot_cli.main graph query 'INVALID CYPHER SYNTAX'" \
    "true"

print_section "PHASE 8: RETRIEVAL & QUERY"

run_test "10-query-basic" \
    "uv run python -m apps.cli.taboot_cli.main query 'what services are running?'"

run_test "10-query-top-k" \
    "uv run python -m apps.cli.taboot_cli.main query 'explain docker compose' --top-k 5"

run_test "10-query-with-sources" \
    "uv run python -m apps.cli.taboot_cli.main query 'configuration' --sources web"

# ============================================================================
# Summary & Results
# ============================================================================

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
print_section "TEST SUMMARY"

echo "Test Results:"
echo -e "  ${GREEN}PASSED${NC}:  $PASSED"
echo -e "  ${RED}FAILED${NC}:  $FAILED"
echo -e "  ${YELLOW}SKIPPED${NC}: $SKIPPED"
echo -e "  ${BLUE}TOTAL${NC}:   $TOTAL"
echo ""

PASS_RATE=0
if [ $TOTAL -gt 0 ]; then
    PASS_RATE=$(( (PASSED * 100) / TOTAL ))
fi

echo "Pass Rate: $PASS_RATE%"
echo "Duration: ${DURATION}s ($(date -u -d @${DURATION} +%M:%S))"
echo ""

# Show failed tests
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed Tests:${NC}"
    for log in "$OUTPUT_DIR"/*_FAIL*.log; do
        if [ -f "$log" ]; then
            echo "  - $(basename "$log" .log)"
        fi
    done
    echo ""
fi

# Show log locations
echo "Logs saved to:"
echo "  $OUTPUT_DIR/"
echo ""

# Generate log summary
echo "Quick log inspection:"
echo "  View all logs:      tail -f $OUTPUT_DIR/*.log"
echo "  Count results:      grep -h '^\[' $OUTPUT_DIR/*.log | sort | uniq -c"
echo "  Failed details:     grep -A5 'FAIL' $OUTPUT_DIR/*.log"
echo ""

# Completion message
END_DATE=$(date)
echo "Test execution completed: $END_DATE"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "Review logs for details"
    exit 1
fi
