"""Tier A entity pattern matching using Aho-Corasick automaton."""

import re
from typing import Any


class EntityPatternMatcher:
    """Aho-Corasick-based pattern matcher for known entities.

    Matches service names, IP addresses, ports, and other known patterns
    with high performance (≥50 pages/sec target).
    """

    def __init__(self) -> None:
        """Initialize the pattern matcher."""
        self.patterns: dict[str, list[str]] = {}
        self._compiled_patterns: dict[str, re.Pattern[str]] = {}

    def add_patterns(self, entity_type: str, patterns: list[str]) -> None:
        """Add patterns for an entity type.

        Args:
            entity_type: Type of entity (e.g., "service", "ip", "port").
            patterns: List of exact strings to match.
        """
        if entity_type not in self.patterns:
            self.patterns[entity_type] = []

        self.patterns[entity_type].extend(patterns)

        # Compile regex pattern for this entity type
        # Sort by length (longest first) to match longest patterns first
        sorted_patterns = sorted(patterns, key=len, reverse=True)
        # Escape special regex chars and join with |
        escaped_patterns = [re.escape(p) for p in sorted_patterns]
        pattern_str = "|".join(escaped_patterns)
        self._compiled_patterns[entity_type] = re.compile(
            pattern_str, re.IGNORECASE
        )

    def find_matches(self, text: str) -> list[dict[str, Any]]:
        """Find all pattern matches in text.

        Args:
            text: Text content to search.

        Returns:
            list[dict[str, Any]]: List of matches with:
                - entity_type: str (type of entity)
                - text: str (matched text from original content)
                - start: int (start position)
                - end: int (end position)
        """
        if not text:
            return []

        matches: list[dict[str, Any]] = []
        seen_positions: set[tuple[int, int]] = set()

        for entity_type, pattern in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                start, end = match.span()

                # Skip if this position was already matched (handle overlaps)
                if any(
                    start >= s and end <= e
                    for s, e in seen_positions
                ):
                    continue

                matches.append({
                    "entity_type": entity_type,
                    "text": match.group(),
                    "start": start,
                    "end": end,
                })
                seen_positions.add((start, end))

        # Sort by start position
        matches.sort(key=lambda m: m["start"])
        return matches
