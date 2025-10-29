#!/usr/bin/env python3
"""Debug script to show exact Firecrawl API parameters being sent.

This script demonstrates:
1. How config values are loaded from environment
2. How params dict is built in WebReader.load_data()
3. The exact format sent to FireCrawlWebReader
4. Parameter naming (snake_case vs camelCase)
"""

import json
import os
from packages.common.config import get_config

def main():
    print("=" * 80)
    print("FIRECRAWL PARAMETER DEBUG")
    print("=" * 80)

    # Step 1: Load config
    config = get_config()

    print("\n[STEP 1] Config Values from Environment")
    print("-" * 80)
    print(f"FIRECRAWL_INCLUDE_PATHS env var: {repr(os.getenv('FIRECRAWL_INCLUDE_PATHS', ''))}")
    print(f"FIRECRAWL_EXCLUDE_PATHS env var: {repr(os.getenv('FIRECRAWL_EXCLUDE_PATHS', ''))}")
    print()
    print(f"config.firecrawl_include_paths: {repr(config.firecrawl_include_paths)}")
    print(f"config.firecrawl_exclude_paths: {repr(config.firecrawl_exclude_paths)}")
    print(f"config.firecrawl_default_country: {repr(config.firecrawl_default_country)}")
    print(f"config.firecrawl_default_languages: {repr(config.firecrawl_default_languages)}")

    # Step 2: Parse config strings to lists (same as web.py lines 207-216)
    print("\n[STEP 2] Parse Comma-Separated Strings to Lists")
    print("-" * 80)

    languages = [lang.strip() for lang in config.firecrawl_default_languages.split(",")]
    print(f"languages: {languages}")

    include_paths = [
        pattern.strip()
        for pattern in config.firecrawl_include_paths.split(",")
        if pattern.strip()
    ]
    exclude_paths = [
        pattern.strip()
        for pattern in config.firecrawl_exclude_paths.split(",")
        if pattern.strip()
    ]

    print(f"include_paths list: {include_paths}")
    print(f"exclude_paths list: {exclude_paths}")
    print(f"include_paths length: {len(include_paths)}")
    print(f"exclude_paths length: {len(exclude_paths)}")

    # Step 3: Build params dict (same as web.py lines 191-222)
    print("\n[STEP 3] Build Params Dict (Python SDK Format - snake_case)")
    print("-" * 80)

    limit = 100  # Example limit

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

    # Add path filtering (same as web.py lines 218-222)
    if include_paths:
        params["include_paths"] = include_paths
    if exclude_paths:
        params["exclude_paths"] = exclude_paths

    print("params dict (as passed to FireCrawlWebReader):")
    print(json.dumps(params, indent=2))

    # Step 4: Show what Firecrawl Python SDK would convert to
    print("\n[STEP 4] Expected HTTP API Format (camelCase - SDK conversion)")
    print("-" * 80)
    print("Note: Firecrawl Python SDK converts snake_case → camelCase internally")
    print()

    # Manual conversion to show what SDK does
    api_params = {
        "scrapeOptions": {
            "formats": params["scrape_options"]["formats"],
            "location": params["scrape_options"]["location"],
        },
        "limit": params.get("limit"),
    }

    if "include_paths" in params:
        api_params["includePaths"] = params["include_paths"]
    if "exclude_paths" in params:
        api_params["excludePaths"] = params["exclude_paths"]

    print("Expected HTTP payload (camelCase):")
    print(json.dumps(api_params, indent=2))

    # Step 5: Validation
    print("\n[STEP 5] Validation")
    print("-" * 80)

    issues = []

    # Check for common mistakes
    if not isinstance(params.get("include_paths"), list) and "include_paths" in params:
        issues.append("❌ include_paths is not a list")
    elif "include_paths" in params:
        print(f"✅ include_paths is list: {params['include_paths']}")
    else:
        print("✅ include_paths not set (allow all)")

    if not isinstance(params.get("exclude_paths"), list) and "exclude_paths" in params:
        issues.append("❌ exclude_paths is not a list")
    elif "exclude_paths" in params:
        print(f"✅ exclude_paths is list: {params['exclude_paths']}")

        # Validate regex patterns
        import re
        for pattern in params["exclude_paths"]:
            try:
                re.compile(pattern)
                print(f"✅ Valid regex pattern: {pattern}")
            except re.error as e:
                issues.append(f"❌ Invalid regex pattern '{pattern}': {e}")
    else:
        print("⚠️  exclude_paths not set (allow all)")

    # Check parameter naming
    if "includePaths" in params or "excludePaths" in params:
        issues.append("❌ CRITICAL: Using camelCase (includePaths/excludePaths) in params dict!")
        issues.append("   Firecrawl Python SDK expects snake_case (include_paths/exclude_paths)")

    # Step 6: Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ ALL CHECKS PASSED")

    print("\nParameter Flow:")
    print("1. Environment variables → TabootConfig (config/__init__.py)")
    print("2. Config values → WebReader.__init__ (lines 72-74)")
    print("3. Config values → WebReader.load_data() (lines 184-222)")
    print("4. params dict → FireCrawlWebReader (line 133)")
    print("5. Python SDK converts snake_case → HTTP API camelCase")
    print("6. HTTP API sends to Firecrawl server")

    print("\nKey Points:")
    print("- ✅ Use snake_case in params dict (include_paths, exclude_paths)")
    print("- ✅ Pass as lists, not strings")
    print("- ✅ Patterns are regex, not globs")
    print("- ✅ SDK handles camelCase conversion automatically")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
