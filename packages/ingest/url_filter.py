"""URL filtering utility for validating include/exclude patterns."""

import logging
import re

logger = logging.getLogger(__name__)


class URLFilter:
    """Validates URLs against include/exclude regex patterns.

    Implements defense-in-depth filtering for Firecrawl URL path patterns.
    """

    def __init__(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Initialize URL filter with regex patterns.

        Args:
            include_patterns: List of regex patterns to include (whitelist).
            exclude_patterns: List of regex patterns to exclude (blacklist).
        """
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]

        logger.debug(
            f"URLFilter initialized: {len(self.include_patterns)} include, "
            f"{len(self.exclude_patterns)} exclude patterns"
        )

    def validate_url(self, url: str) -> tuple[bool, str | None]:
        """Check if URL should be allowed.

        Args:
            url: URL to validate.

        Returns:
            Tuple of (is_allowed, reason).
            is_allowed: True if URL passes filters.
            reason: String explaining why URL was rejected (None if allowed).
        """
        # If include patterns exist, URL must match at least one
        if self.include_patterns and not any(
            pattern.search(url) for pattern in self.include_patterns
        ):
            return False, f"URL does not match any include patterns: {url}"

        # If exclude patterns exist, URL must not match any
        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                if pattern.search(url):
                    return False, f"URL matches exclude pattern {pattern.pattern}: {url}"

        return True, None

    def filter_urls(self, urls: list[str]) -> list[str]:
        """Filter list of URLs, keeping only allowed ones.

        Args:
            urls: List of URLs to filter.

        Returns:
            List of allowed URLs.
        """
        allowed = []
        for url in urls:
            is_allowed, reason = self.validate_url(url)
            if is_allowed:
                allowed.append(url)
            else:
                logger.debug(f"Filtered out URL: {reason}")
        return allowed
