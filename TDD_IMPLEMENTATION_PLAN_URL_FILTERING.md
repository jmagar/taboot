# TDD Implementation Plan: Firecrawl URL Filtering for English-Only Content

## Executive Summary

This plan implements URL path filtering to prevent Firecrawl from crawling non-English language pages using `includePaths` and `excludePaths` regex parameters. The implementation follows strict TDD principles with clear Red-Green-Refactor phases that can be executed autonomously.

---

## Phase 1: RED (Write Failing Tests)

### 1.1 Test File: `/home/jmagar/code/taboot/tests/packages/ingest/readers/test_web_reader.py`

**Objective:** Add new test methods that verify URL filtering parameters are passed correctly to FireCrawlWebReader.

**Tests to Add:**

```python
def test_web_reader_passes_exclude_paths_to_firecrawl(self) -> None:
    """Test that WebReader passes excludePaths parameter to Firecrawl.

    Firecrawl v2 supports excludePaths with regex patterns to blacklist URL paths.
    Patterns match against URL pathname only (not full URL).
    """
    from packages.ingest.readers.web import WebReader
    from unittest.mock import patch, MagicMock

    with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
        mock_reader_instance = MagicMock()
        mock_reader_instance.load_data.return_value = []
        mock_reader_class.return_value = mock_reader_instance

        # Create WebReader (config should have default exclude patterns)
        web_reader = WebReader(
            firecrawl_url="http://test:3002",
            firecrawl_api_key="test-key"
        )

        # Call load_data
        web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

        # Verify excludePaths parameter was passed
        call_kwargs = mock_reader_class.call_args[1]
        params = call_kwargs["params"]

        assert "excludePaths" in params, "excludePaths should be in params"
        assert isinstance(params["excludePaths"], list), "excludePaths should be a list"
        assert len(params["excludePaths"]) > 0, "excludePaths should not be empty by default"

def test_web_reader_passes_include_paths_to_firecrawl(self) -> None:
    """Test that WebReader passes includePaths parameter when configured.

    Firecrawl v2 supports includePaths with regex patterns to whitelist URL paths.
    """
    from packages.ingest.readers.web import WebReader
    from unittest.mock import patch, MagicMock, Mock
    from packages.common.config import get_config

    # Mock config to return custom includePaths
    with patch("packages.ingest.readers.web.get_config") as mock_config:
        mock_cfg = Mock()
        mock_cfg.firecrawl_default_country = "US"
        mock_cfg.firecrawl_default_languages = "en-US"
        mock_cfg.firecrawl_include_paths = "^/en/.*$,^/docs/.*$"  # Comma-separated
        mock_cfg.firecrawl_exclude_paths = ""
        mock_config.return_value = mock_cfg

        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            web_reader = WebReader(
                firecrawl_url="http://test:3002",
                firecrawl_api_key="test-key"
            )

            web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

            # Verify includePaths parameter
            call_kwargs = mock_reader_class.call_args[1]
            params = call_kwargs["params"]

            assert "includePaths" in params, "includePaths should be in params"
            assert isinstance(params["includePaths"], list), "includePaths should be a list"
            assert len(params["includePaths"]) == 2, "Should have 2 include patterns"
            assert "^/en/.*$" in params["includePaths"]
            assert "^/docs/.*$" in params["includePaths"]

def test_web_reader_exclude_paths_defaults_to_common_languages(self) -> None:
    """Test that excludePaths defaults block common non-English languages.

    Default should block: de, fr, es, it, pt, nl, pl, ru, ja, zh, ko, ar, tr, cs, da, sv, no
    """
    from packages.ingest.readers.web import WebReader
    from unittest.mock import patch, MagicMock

    with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
        mock_reader_instance = MagicMock()
        mock_reader_instance.load_data.return_value = []
        mock_reader_class.return_value = mock_reader_instance

        web_reader = WebReader(
            firecrawl_url="http://test:3002",
            firecrawl_api_key="test-key"
        )

        web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

        call_kwargs = mock_reader_class.call_args[1]
        params = call_kwargs["params"]
        exclude_patterns = params.get("excludePaths", [])

        # Verify pattern blocks common languages
        assert len(exclude_patterns) > 0, "Should have default exclude patterns"

        # Check that pattern includes common language codes
        pattern_str = '|'.join(exclude_patterns)
        assert "de" in pattern_str or "/de/" in pattern_str, "Should block German"
        assert "fr" in pattern_str or "/fr/" in pattern_str, "Should block French"
        assert "es" in pattern_str or "/es/" in pattern_str, "Should block Spanish"

def test_web_reader_parses_comma_separated_patterns(self) -> None:
    """Test that WebReader correctly parses comma-separated pattern strings.

    Config values come as comma-separated strings and must be split into lists.
    """
    from packages.ingest.readers.web import WebReader
    from unittest.mock import patch, MagicMock, Mock

    with patch("packages.ingest.readers.web.get_config") as mock_config:
        mock_cfg = Mock()
        mock_cfg.firecrawl_default_country = "US"
        mock_cfg.firecrawl_default_languages = "en-US"
        mock_cfg.firecrawl_include_paths = "^/en/.*$, ^/docs/.*$ , ^/api/.*$"  # Whitespace variations
        mock_cfg.firecrawl_exclude_paths = "^/de/.*$,^/fr/.*$"
        mock_config.return_value = mock_cfg

        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            web_reader = WebReader(
                firecrawl_url="http://test:3002",
                firecrawl_api_key="test-key"
            )

            web_reader.load_data("https://example.com", limit=5)

            call_kwargs = mock_reader_class.call_args[1]
            params = call_kwargs["params"]

            # Verify parsing with whitespace handling
            assert len(params["includePaths"]) == 3, "Should parse 3 include patterns"
            assert "^/en/.*$" in params["includePaths"]
            assert "^/docs/.*$" in params["includePaths"]
            assert "^/api/.*$" in params["includePaths"]

            assert len(params["excludePaths"]) == 2, "Should parse 2 exclude patterns"
            assert "^/de/.*$" in params["excludePaths"]
            assert "^/fr/.*$" in params["excludePaths"]

def test_web_reader_empty_patterns_not_included(self) -> None:
    """Test that empty pattern strings don't result in empty list items.

    Handles edge cases like trailing commas or multiple commas.
    """
    from packages.ingest.readers.web import WebReader
    from unittest.mock import patch, MagicMock, Mock

    with patch("packages.ingest.readers.web.get_config") as mock_config:
        mock_cfg = Mock()
        mock_cfg.firecrawl_default_country = "US"
        mock_cfg.firecrawl_default_languages = "en-US"
        mock_cfg.firecrawl_include_paths = "^/en/.*$,,"  # Trailing commas
        mock_cfg.firecrawl_exclude_paths = ""  # Empty string
        mock_config.return_value = mock_cfg

        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            web_reader = WebReader(
                firecrawl_url="http://test:3002",
                firecrawl_api_key="test-key"
            )

            web_reader.load_data("https://example.com", limit=5)

            call_kwargs = mock_reader_class.call_args[1]
            params = call_kwargs["params"]

            # Verify no empty strings in lists
            include_paths = params.get("includePaths", [])
            for pattern in include_paths:
                assert pattern.strip() != "", "No empty patterns should be in includePaths"

            # Verify empty config doesn't add key
            assert "excludePaths" not in params or params["excludePaths"] == [], \
                "Empty excludePaths config should not add parameter"
```

**Commands to Run (Expected to FAIL):**

```bash
# Run new tests only (they will fail - this is RED phase)
uv run pytest tests/packages/ingest/readers/test_web_reader.py::TestWebReader::test_web_reader_passes_exclude_paths_to_firecrawl -v
uv run pytest tests/packages/ingest/readers/test_web_reader.py::TestWebReader::test_web_reader_passes_include_paths_to_firecrawl -v
uv run pytest tests/packages/ingest/readers/test_web_reader.py::TestWebReader::test_web_reader_exclude_paths_defaults_to_common_languages -v
uv run pytest tests/packages/ingest/readers/test_web_reader.py::TestWebReader::test_web_reader_parses_comma_separated_patterns -v
uv run pytest tests/packages/ingest/readers/test_web_reader.py::TestWebReader::test_web_reader_empty_patterns_not_included -v

# Run all WebReader tests (existing should pass, new should fail)
uv run pytest tests/packages/ingest/readers/test_web_reader.py -v
```

**Expected Failures:**
- `KeyError: 'excludePaths'` - params dict doesn't include excludePaths
- `KeyError: 'includePaths'` - params dict doesn't include includePaths
- `AttributeError: 'TabootConfig' object has no attribute 'firecrawl_include_paths'` - config missing new fields
- `AttributeError: 'TabootConfig' object has no attribute 'firecrawl_exclude_paths'` - config missing new fields

---

## Phase 2: GREEN (Implement Features)

### 2.1 Config Changes: `/home/jmagar/code/taboot/packages/common/config/__init__.py`

**Location:** After line 238 (after `firecrawl_default_languages`)

**Code to Add:**

```python
    # Firecrawl URL path filtering (Firecrawl v2 feature)
    # includePaths: Whitelist regex patterns for URL paths to crawl
    # excludePaths: Blacklist regex patterns for URL paths to skip (takes precedence)
    # Patterns match against pathname only (e.g., "/en/docs/api" not "https://example.com/en/docs/api")
    # Comma-separated strings parsed to lists
    firecrawl_include_paths: str = ""  # Empty = allow all paths
    firecrawl_exclude_paths: str = (
        # Default: Block common non-English language path segments
        # Matches patterns like: /de/..., /docs/de/..., /api/fr/..., etc.
        r"^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"
    )
```

**Type Annotations:** Both fields are `str` because environment variables come as strings. They will be parsed to `list[str]` in the WebReader.

**Docstrings Added:** Inline comments explain:
- What includePaths/excludePaths do
- Precedence (exclude wins)
- Pattern format (pathname only)
- Comma-separated parsing

**Default Values:**
- `firecrawl_include_paths = ""` (empty, allow all by default)
- `firecrawl_exclude_paths` = regex blocking 17 common languages

### 2.2 WebReader Changes: `/home/jmagar/code/taboot/packages/ingest/readers/web.py`

**Location:** Inside `load_data()` method, after building the `location` parameter (after line 149)

**Code to Add:**

```python
        # Build path filtering parameters (Firecrawl v2 URL filtering)
        # includePaths: Whitelist regex patterns for paths to crawl
        # excludePaths: Blacklist regex patterns for paths to skip (takes precedence)
        # Parse comma-separated config strings into lists, filtering empty strings
        include_paths: list[str] = [
            pattern.strip()
            for pattern in config.firecrawl_include_paths.split(",")
            if pattern.strip()
        ]
        exclude_paths: list[str] = [
            pattern.strip()
            for pattern in config.firecrawl_exclude_paths.split(",")
            if pattern.strip()
        ]

        # Add to params if non-empty
        if include_paths:
            params["includePaths"] = include_paths
        if exclude_paths:
            params["excludePaths"] = exclude_paths
```

**Logic Explanation:**
1. Parse comma-separated strings with `.split(",")`
2. Strip whitespace from each pattern with `.strip()`
3. Filter out empty strings with list comprehension `if pattern.strip()`
4. Only add to params if lists are non-empty (Firecrawl ignores empty lists)

**Updated `load_data()` method signature:** No changes needed - filtering is transparent.

**Full context of where this goes:**

```python
# Existing code (around line 140-150)
params: dict[str, object] = {
    "scrape_options": {
        "formats": ["markdown"],
        "location": {
            "country": config.firecrawl_default_country,
            "languages": languages,
        },
    }
}
if limit is not None:
    params["limit"] = limit

# <<<< INSERT NEW CODE HERE >>>>

try:
    docs = self._fetch_with_firecrawl(url, params)
    # ... rest of method
```

### 2.3 Environment Variable Documentation: `.env.example`

**Location:** After line 17 (after `FIRECRAWL_DEFAULT_LANGUAGES`)

**Code to Add:**

```bash
# Firecrawl URL path filtering (Firecrawl v2 feature)
# Control which URL paths are crawled based on regex patterns
# NOTE: Patterns match pathname only (e.g., "/en/docs/api" not full URL)
# NOTE: excludePaths takes precedence over includePaths

# FIRECRAWL_INCLUDE_PATHS: Whitelist patterns (comma-separated regex)
# Empty = allow all paths (default)
# Example: "^/en/.*$,^/docs/.*$" (only crawl /en/* and /docs/* paths)
FIRECRAWL_INCLUDE_PATHS=""

# FIRECRAWL_EXCLUDE_PATHS: Blacklist patterns (comma-separated regex)
# Default blocks common non-English language paths: /de/, /fr/, /es/, etc.
# Empty = allow all paths (no blocking)
# Example: "^/de/.*$,^/fr/.*$" (block German and French paths)
FIRECRAWL_EXCLUDE_PATHS="^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"

# Common use cases:
# 1. English-only (default above): Blocks 17 common languages
# 2. Specific path prefix: FIRECRAWL_INCLUDE_PATHS="^/en/.*$" (only /en/*)
# 3. Multiple languages: FIRECRAWL_EXCLUDE_PATHS="^.*/(de|fr)/.*$" (block DE/FR only)
# 4. No filtering: FIRECRAWL_EXCLUDE_PATHS="" (crawl everything)
```

**Comments Explain:**
- Pattern format (pathname only)
- Precedence rule
- Default values
- Common use cases
- How to disable filtering

**Commands to Run (Expected to PASS):**

```bash
# Run all WebReader tests (should now pass)
uv run pytest tests/packages/ingest/readers/test_web_reader.py -v

# Verify no regressions in other ingest tests
uv run pytest tests/packages/ingest/ -v -m "not slow"

# Check type annotations
uv run mypy packages/ingest/readers/web.py
uv run mypy packages/common/config/__init__.py

# Verify config loads without errors
uv run python -c "from packages.common.config import get_config; cfg = get_config(); print(f'Include: {cfg.firecrawl_include_paths}'); print(f'Exclude: {cfg.firecrawl_exclude_paths}')"
```

**Expected Results:**
- All 12 tests in `test_web_reader.py` pass (7 existing + 5 new)
- Mypy type checking passes with no errors
- Config loads successfully and prints default values

---

## Phase 3: REFACTOR (Code Quality & Documentation)

### 3.1 Code Quality Checks

**Commands to Run:**

```bash
# Format code with Ruff
uv run ruff format packages/ingest/readers/web.py packages/common/config/__init__.py tests/packages/ingest/readers/test_web_reader.py

# Lint code with Ruff
uv run ruff check packages/ingest/readers/web.py packages/common/config/__init__.py tests/packages/ingest/readers/test_web_reader.py

# Type check with mypy (strict mode)
uv run mypy packages/ingest/readers/web.py packages/common/config/__init__.py

# Run full test suite to ensure no regressions
uv run pytest tests/packages/ingest/ -v -m "not slow"
uv run pytest tests/packages/common/ -v -m "not slow"

# Check test coverage for modified files
uv run pytest --cov=packages.ingest.readers.web --cov=packages.common.config tests/packages/ingest/readers/test_web_reader.py -v
```

**Expected Results:**
- Ruff format: No changes needed (already formatted)
- Ruff lint: No errors or warnings
- Mypy: No type errors
- Tests: All pass (no regressions)
- Coverage: WebReader `load_data()` method should have 100% branch coverage for path filtering logic

### 3.2 Documentation Updates

**Files to Update:**

#### `/home/jmagar/code/taboot/CLAUDE.md`

**Location:** After line 237 (in "Firecrawl Config" section)

**Code to Add:**

```markdown
    # Firecrawl URL path filtering (Firecrawl v2 feature)
    firecrawl_include_paths: str = ""  # Comma-separated regex patterns (whitelist)
    firecrawl_exclude_paths: str = "..."  # Comma-separated regex patterns (blacklist, default blocks 17 languages)
```

#### `/home/jmagar/code/taboot/packages/ingest/readers/web.py` (Docstring Update)

**Location:** Update class docstring (after line 32)

**Updated Docstring:**

```python
class WebReader:
    """Web document reader using Firecrawl API.

    Implements rate limiting, error handling, robots.txt compliance, and URL path filtering.

    Path Filtering (Firecrawl v2):
    - includePaths: Whitelist regex patterns for URL paths to crawl
    - excludePaths: Blacklist regex patterns for URL paths to skip (takes precedence)
    - Patterns match pathname only (e.g., "/en/docs" not "https://example.com/en/docs")
    - Configured via FIRECRAWL_INCLUDE_PATHS and FIRECRAWL_EXCLUDE_PATHS environment variables
    - Default: Blocks 17 common non-English language paths (de, fr, es, etc.)
    """
```

#### Create: `/home/jmagar/code/taboot/docs/FIRECRAWL_URL_FILTERING.md`

**Content:**

```markdown
# Firecrawl URL Path Filtering Guide

## Overview

WebReader supports URL path filtering via Firecrawl v2 parameters to control which pages are crawled.

## Configuration

### Environment Variables

- **FIRECRAWL_INCLUDE_PATHS**: Whitelist regex patterns (comma-separated)
  - Empty = allow all paths (default)
  - Example: `"^/en/.*$,^/docs/.*$"` (only crawl /en/* and /docs/* paths)

- **FIRECRAWL_EXCLUDE_PATHS**: Blacklist regex patterns (comma-separated)
  - Takes precedence over includePaths
  - Default: `"^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"`
  - Blocks 17 common non-English language paths

## Pattern Format

- **JavaScript regex** (Firecrawl is Node.js-based)
- **Pathname matching only** (e.g., `/path/to/page` not `https://example.com/path/to/page`)
- **Case-sensitive** by default
- **Anchors**: Use `^` and `$` for precise matching

## Common Patterns

```bash
# English-only (default)
FIRECRAWL_EXCLUDE_PATHS="^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"

# Specific path prefix
FIRECRAWL_INCLUDE_PATHS="^/en/.*$"

# Multiple specific paths
FIRECRAWL_INCLUDE_PATHS="^/en/.*$,^/docs/.*$,^/api/.*$"

# Block admin/private pages
FIRECRAWL_EXCLUDE_PATHS="^/admin/.*$,^/private/.*$"

# No filtering (crawl everything)
FIRECRAWL_EXCLUDE_PATHS=""
FIRECRAWL_INCLUDE_PATHS=""
```

## Use Cases

### 1. English-Only Documentation

**Goal**: Crawl English docs, block all other languages

```bash
FIRECRAWL_EXCLUDE_PATHS="^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"
```

### 2. Specific Section

**Goal**: Only crawl `/en/docs/*` paths

```bash
FIRECRAWL_INCLUDE_PATHS="^/en/docs/.*$"
```

### 3. Multiple Sections

**Goal**: Crawl docs and API reference only

```bash
FIRECRAWL_INCLUDE_PATHS="^/en/docs/.*$,^/en/api/.*$"
```

### 4. Block Specific Languages

**Goal**: Block only German and French

```bash
FIRECRAWL_EXCLUDE_PATHS="^.*/(de|fr)/.*$"
```

## Precedence Rules

1. **includePaths** is checked first (if specified)
2. **excludePaths** is checked second
3. **excludePaths takes precedence**: If a URL matches both, it's excluded

## Testing Patterns

Use [regex101.com](https://regex101.com) to test patterns before deploying:

1. Select "JavaScript" flavor
2. Test against pathname only (e.g., `/en/docs/api`)
3. Verify matches/non-matches

## Limitations

- Patterns apply only to same-domain URLs
- External links controlled by `allowExternalLinks` parameter (not affected by path patterns)
- Base URL must match includePaths or you'll get "Source URL is not allowed" error

## Troubleshooting

### Issue: Pages still being crawled despite exclude pattern

**Check**:
1. Pattern matches pathname only (not full URL)
2. Pattern uses correct regex syntax (JavaScript flavor)
3. Pattern is properly escaped (e.g., `\.` for literal dot)
4. Config loaded correctly (`uv run python -c "from packages.common.config import get_config; print(get_config().firecrawl_exclude_paths)"`)

### Issue: No pages being crawled

**Check**:
1. includePaths pattern matches your base URL
2. includePaths and excludePaths don't conflict
3. Patterns use anchors correctly (`^` and `$`)

## Performance Impact

- **Minimal**: Filtering happens in Firecrawl server (not Python)
- More restrictive patterns = faster crawls (fewer pages processed)
- No impact on embedding/ingestion pipeline

## Version Requirements

- Requires **Firecrawl v2** (v1 doesn't support includePaths/excludePaths)
- Verify version: `docker compose logs taboot-crawler | grep version`
```

---

## Phase 4: Real-World Verification

### 4.1 Database Cleanup

**Objective:** Remove German content from existing crawls to verify filtering works.

**Commands:**

```bash
# 1. Delete German content from PostgreSQL
docker compose exec -e PGPASSWORD="zFp9g998BFwHuvsB9DcjerW8DyuNMQv2" taboot-db psql -U taboot -d taboot -c