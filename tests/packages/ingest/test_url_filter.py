"""Tests for URL filtering utility."""

import pytest
from packages.ingest.url_filter import URLFilter


def test_no_patterns_allows_all() -> None:
    """With no patterns, all URLs should be allowed."""
    url_filter = URLFilter()
    is_allowed, reason = url_filter.validate_url("https://example.com")
    assert is_allowed
    assert reason is None


def test_exclude_pattern_blocks_url() -> None:
    """Exclude pattern should block matching URLs."""
    url_filter = URLFilter(exclude_patterns=[r"^.*/de/.*$"])
    is_allowed, reason = url_filter.validate_url("https://example.com/de/docs")
    assert not is_allowed
    assert "exclude pattern" in reason
    assert "^.*/de/.*$" in reason


def test_include_pattern_allows_url() -> None:
    """Include pattern should allow matching URLs."""
    url_filter = URLFilter(include_patterns=[r"^/en/.*$"])
    is_allowed, reason = url_filter.validate_url("https://example.com/en/docs")
    assert is_allowed
    assert reason is None


def test_include_pattern_blocks_non_matching() -> None:
    """Include pattern should block non-matching URLs."""
    url_filter = URLFilter(include_patterns=[r"^/en/.*$"])
    is_allowed, reason = url_filter.validate_url("https://example.com/de/docs")
    assert not is_allowed
    assert "does not match" in reason


def test_exclude_takes_precedence() -> None:
    """Exclude patterns should take precedence over include."""
    url_filter = URLFilter(
        include_patterns=[r"^/docs/.*$"],
        exclude_patterns=[r"^.*/de/.*$"],
    )
    is_allowed, _ = url_filter.validate_url("https://example.com/docs/de/api")
    assert not is_allowed


def test_filter_urls_list() -> None:
    """filter_urls should filter list correctly."""
    url_filter = URLFilter(exclude_patterns=[r"^/de/.*$"])
    urls = [
        "https://example.com/en/docs",
        "https://example.com/de/docs",
        "https://example.com/fr/docs",
    ]
    allowed = url_filter.filter_urls(urls)
    assert len(allowed) == 2
    assert "https://example.com/de/docs" not in allowed


def test_multiple_exclude_patterns() -> None:
    """Multiple exclude patterns should all be checked."""
    url_filter = URLFilter(exclude_patterns=[r"^.*/de/.*$", r"^.*/fr/.*$", r"^.*/es/.*$"])

    # Test that all patterns are enforced
    assert not url_filter.validate_url("https://example.com/de/docs")[0]
    assert not url_filter.validate_url("https://example.com/fr/docs")[0]
    assert not url_filter.validate_url("https://example.com/es/docs")[0]

    # Test that non-matching URLs pass
    assert url_filter.validate_url("https://example.com/en/docs")[0]


def test_multiple_include_patterns() -> None:
    """Multiple include patterns should allow any match."""
    url_filter = URLFilter(include_patterns=[r"^/en/.*$", r"^/docs/.*$"])

    # Both patterns should allow URLs
    assert url_filter.validate_url("https://example.com/en/api")[0]
    assert url_filter.validate_url("https://example.com/docs/guide")[0]

    # Non-matching should be rejected
    assert not url_filter.validate_url("https://example.com/about")[0]


def test_real_world_language_exclusion() -> None:
    """Test realistic language exclusion pattern from config."""
    # Pattern from default config: blocks 17 common non-English languages
    url_filter = URLFilter(
        exclude_patterns=[
            r"^.*/(de|fr|es|it|pt|nl|pl|ru|ja|zh|ko|ar|tr|cs|da|sv|no)/.*$"
        ]
    )

    # Should block common non-English paths
    assert not url_filter.validate_url("https://docs.anthropic.com/de/docs/intro")[0]
    assert not url_filter.validate_url("https://docs.anthropic.com/fr/api/reference")[0]
    assert not url_filter.validate_url("https://docs.anthropic.com/ja/claude")[0]

    # Should allow English paths
    assert url_filter.validate_url("https://docs.anthropic.com/en/docs/intro")[0]
    assert url_filter.validate_url("https://docs.anthropic.com/docs/intro")[0]

    # Should allow root paths without language code
    assert url_filter.validate_url("https://docs.anthropic.com/")[0]


def test_empty_url() -> None:
    """Empty URL should be allowed if no patterns specified."""
    url_filter = URLFilter()
    is_allowed, reason = url_filter.validate_url("")
    assert is_allowed
    assert reason is None


def test_url_with_query_params() -> None:
    """URLs with query parameters should match patterns correctly."""
    url_filter = URLFilter(exclude_patterns=[r"^/de/.*$"])

    # Query params should not interfere with matching
    assert not url_filter.validate_url("https://example.com/de/docs?version=1.0")[0]
    assert url_filter.validate_url("https://example.com/en/docs?version=1.0")[0]


def test_url_with_fragment() -> None:
    """URLs with fragments should match patterns correctly."""
    url_filter = URLFilter(exclude_patterns=[r"^/de/.*$"])

    # Fragments should not interfere with matching
    assert not url_filter.validate_url("https://example.com/de/docs#section")[0]
    assert url_filter.validate_url("https://example.com/en/docs#section")[0]


def test_filter_urls_preserves_order() -> None:
    """filter_urls should preserve order of allowed URLs."""
    url_filter = URLFilter(exclude_patterns=[r"^/de/.*$"])
    urls = [
        "https://example.com/en/docs",
        "https://example.com/de/docs",  # filtered out
        "https://example.com/fr/docs",
        "https://example.com/de/api",   # filtered out
        "https://example.com/it/docs",
    ]
    allowed = url_filter.filter_urls(urls)

    assert allowed == [
        "https://example.com/en/docs",
        "https://example.com/fr/docs",
        "https://example.com/it/docs",
    ]


def test_case_sensitive_matching() -> None:
    """Pattern matching should be case-sensitive by default."""
    url_filter = URLFilter(exclude_patterns=[r"^/DE/.*$"])

    # Should block uppercase DE
    assert not url_filter.validate_url("https://example.com/DE/docs")[0]

    # Should allow lowercase de (case-sensitive)
    assert url_filter.validate_url("https://example.com/de/docs")[0]


def test_complex_pattern_with_anchors() -> None:
    """Complex regex patterns with anchors should work correctly."""
    url_filter = URLFilter(
        include_patterns=[r"^https://docs\.example\.com/.*"],
        exclude_patterns=[r"^.*/(archive|deprecated)/.*$"],
    )

    # Should allow docs subdomain
    assert url_filter.validate_url("https://docs.example.com/api/reference")[0]

    # Should block non-docs subdomain
    assert not url_filter.validate_url("https://www.example.com/api/reference")[0]

    # Should block archived docs
    assert not url_filter.validate_url("https://docs.example.com/archive/old-api")[0]
