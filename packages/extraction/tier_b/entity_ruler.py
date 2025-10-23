"""Tier B spaCy entity ruler for Service, Host, IP, Port extraction."""

import re
from typing import Any


class SpacyEntityRuler:
    """Pattern-based entity extractor for technical entities.

    Target: ≥200 sentences/sec.
    Note: Uses regex patterns instead of spaCy models for deployment simplicity.
    """

    def __init__(self, model: str = "en_core_web_sm"):
        """Initialize entity ruler.

        Args:
            model: Model name (unused, kept for API compatibility).
        """
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> dict[str, re.Pattern[str]]:
        """Build regex patterns for entity extraction.

        Returns:
            dict[str, re.Pattern]: Compiled regex patterns by entity type.
        """
        return {
            "SERVICE": re.compile(
                r"\b(nginx|postgres|postgresql|redis|mongodb|mysql|"
                r"elasticsearch|kafka|rabbitmq|docker|kubernetes|"
                r"api[\-\s]?service|database|cache|queue|storage|"
                r"\w+\-service)\b",
                re.IGNORECASE
            ),
            "IP": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
            "PORT": re.compile(r"\b(?:port\s+)?(\d{2,5})\b|\:(\d{2,5})\b", re.IGNORECASE),
            "HOST": re.compile(
                r"\b(server\d+|host\d+|\w+\.example\.com|\w+\-host)\b",
                re.IGNORECASE
            ),
        }

    def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract entities from text using regex patterns.

        Args:
            text: Input text to process.

        Returns:
            list[dict[str, Any]]: Extracted entities with label, text, start, end.
        """
        if not text:
            return []

        entities = []

        # Extract each entity type
        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # For PORT pattern, get the actual port number from groups
                if label == "PORT":
                    port_text = match.group(1) or match.group(2)
                    if port_text:
                        # Find the actual position of the port number
                        port_start = match.start() if match.group(1) else match.start() + 1
                        entities.append({
                            "label": label,
                            "text": port_text,
                            "start": port_start,
                            "end": port_start + len(port_text),
                        })
                else:
                    entities.append({
                        "label": label,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    })

        # Deduplicate and sort by position
        seen_positions = set()
        unique_entities = []
        for entity in entities:
            pos = (entity["start"], entity["end"])
            if pos not in seen_positions:
                seen_positions.add(pos)
                unique_entities.append(entity)

        unique_entities.sort(key=lambda e: e["start"])
        return unique_entities
