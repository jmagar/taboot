# Firecrawl URL Path Filtering Guide

## Overview

WebReader supports URL path filtering via Firecrawl v2 parameters to control which pages are crawled.

## Configuration

### Environment Variables

- **FIRECRAWL_INCLUDE_PATHS**: Whitelist regex patterns (comma-separated)
  - Empty = allow all paths (default)
  - Example: `"^/en/.*$,^/docs/.*$"` (only crawl /en/* and /docs/* paths)

- **FIRECRAWL_EXCLUDE_PATHS**: Blacklist regex patterns (comma-separated)
  - Takes precedence over include_paths
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

1. **include_paths** is checked first (if specified)
2. **exclude_paths** is checked second
3. **exclude_paths takes precedence**: If a URL matches both, it's excluded

## Testing Patterns

Use [regex101.com](https://regex101.com) to test patterns before deploying:

1. Select "JavaScript" flavor
2. Test against pathname only (e.g., `/en/docs/api`)
3. Verify matches/non-matches

## Limitations

- Patterns apply only to same-domain URLs
- External links controlled by `allowExternalLinks` parameter (not affected by path patterns)
- Base URL must match include_paths or you'll get "Source URL is not allowed" error

## Troubleshooting

### Issue: Pages still being crawled despite exclude pattern

**Check**:
1. Pattern matches pathname only (not full URL)
2. Pattern uses correct regex syntax (JavaScript flavor)
3. Pattern is properly escaped (e.g., `\.` for literal dot)
4. Config loaded correctly (`uv run python -c "from packages.common.config import get_config; print(get_config().firecrawl_exclude_paths)"`)

### Issue: No pages being crawled

**Check**:
1. include_paths pattern matches your base URL
2. include_paths and exclude_paths don't conflict
3. Patterns use anchors correctly (`^` and `$`)

## Performance Impact

- **Minimal**: Filtering happens in Firecrawl server (not Python)
- More restrictive patterns = faster crawls (fewer pages processed)
- No impact on embedding/ingestion pipeline

## Version Requirements

- Requires **Firecrawl v2** (v1 doesn't support include_paths/exclude_paths)
- Verify version: `docker compose logs taboot-crawler | grep version`
