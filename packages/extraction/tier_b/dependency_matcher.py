"""Tier B dependency matcher for relationship extraction."""

import re
from typing import Any


class DependencyMatcher:
    """Extract relationships between entities using dependency patterns.

    Identifies DEPENDS_ON, ROUTES_TO, CONNECTS_TO relationships.
    """

    def __init__(self) -> None:
        """Initialize dependency matcher with relationship patterns."""
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> dict[str, re.Pattern[str]]:
        """Build regex patterns for relationship extraction.

        Returns:
            dict[str, re.Pattern]: Compiled patterns by relationship type.
        """
        return {
            "DEPENDS_ON": re.compile(
                r"(\w+(?:\-\w+)*)\s+(?:depends?\s+on|requires?|needs?)\s+(\w+(?:\-\w+)*)",
                re.IGNORECASE,
            ),
            "ROUTES_TO": re.compile(
                r"(\w+)\s+(?:routes?|forwards?|proxies?)\s+(?:requests?\s+)?(?:to\s+)?(\w+(?:\-\w+)*)",
                re.IGNORECASE,
            ),
            "CONNECTS_TO": re.compile(
                r"(\w+(?:\-\w+)*)\s+(?:connects?\s+to|links?\s+to)\s+(\w+(?:\-\w+)*)", re.IGNORECASE
            ),
        }

    def extract_relationships(self, text: str) -> list[dict[str, Any]]:
        """Extract relationships from text.

        Args:
            text: Input text to process.

        Returns:
            list[dict[str, Any]]: Extracted relationships with:
                - type: str (relationship type)
                - source: str (source entity)
                - target: str (target entity)
                - span: str (matched text)
        """
        if not text:
            return []

        relationships = []

        for rel_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                source = match.group(1)
                target = match.group(2)

                relationships.append(
                    {
                        "type": rel_type,
                        "source": source,
                        "target": target,
                        "span": match.group(),
                    }
                )

        return relationships
