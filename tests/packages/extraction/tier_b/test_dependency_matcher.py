"""Tests for Tier B dependency matcher for relationship extraction."""

import pytest

from packages.extraction.tier_b.dependency_matcher import DependencyMatcher


class TestDependencyMatcher:
    """Test relationship extraction (DEPENDS_ON, ROUTES_TO)."""

    @pytest.fixture
    def matcher(self):
        """Create dependency matcher instance."""
        return DependencyMatcher()

    def test_extract_depends_on_relationship(self, matcher):
        """Test extracting DEPENDS_ON relationships."""
        text = "The api-service depends on postgres and redis."

        relationships = matcher.extract_relationships(text)

        depends_on = [r for r in relationships if r["type"] == "DEPENDS_ON"]
        assert len(depends_on) >= 1

    def test_extract_routes_to_relationship(self, matcher):
        """Test extracting ROUTES_TO relationships."""
        text = "nginx routes requests to api-service on port 8080."

        relationships = matcher.extract_relationships(text)

        routes_to = [r for r in relationships if r["type"] == "ROUTES_TO"]
        assert len(routes_to) >= 1

    def test_extract_connects_to_relationship(self, matcher):
        """Test extracting CONNECTS_TO relationships."""
        text = "The application connects to database at server01:5432."

        relationships = matcher.extract_relationships(text)

        connects_to = [r for r in relationships if r["type"] == "CONNECTS_TO"]
        assert len(connects_to) >= 1

    def test_empty_text_returns_empty(self, matcher):
        """Test empty text returns empty list."""
        relationships = matcher.extract_relationships("")
        assert relationships == []

    def test_text_without_relationships(self, matcher):
        """Test text without relationships."""
        text = "This is just plain text."
        relationships = matcher.extract_relationships(text)
        assert isinstance(relationships, list)
