"""Tests for Tier B window selector for Tier C LLM processing."""

import pytest
from packages.extraction.tier_b.window_selector import WindowSelector


class TestWindowSelector:
    """Test micro-window selection (≤512 tokens) for Tier C."""

    @pytest.fixture
    def selector(self):
        """Create window selector instance."""
        return WindowSelector(max_tokens=512)

    def test_select_windows_from_short_text(self, selector):
        """Test selecting windows from short text."""
        text = "The api-service connects to postgres database."

        windows = selector.select_windows(text)

        assert len(windows) >= 1
        assert all(w["token_count"] <= 512 for w in windows)

    def test_select_windows_from_long_text(self, selector):
        """Test selecting windows from long text that needs splitting."""
        # Create text with multiple sentences
        text = " ".join([f"Sentence {i} about services and dependencies." for i in range(100)])

        windows = selector.select_windows(text)

        assert len(windows) >= 1
        assert all(w["token_count"] <= 512 for w in windows)

    def test_window_has_required_fields(self, selector):
        """Test that windows have required fields."""
        text = "The nginx proxy routes to api-service."

        windows = selector.select_windows(text)

        assert len(windows) >= 1
        window = windows[0]
        assert "content" in window
        assert "token_count" in window
        assert "start" in window
        assert "end" in window

    def test_empty_text_returns_empty(self, selector):
        """Test empty text returns empty list."""
        windows = selector.select_windows("")
        assert windows == []

    def test_respects_max_tokens(self, selector):
        """Test that windows respect max token limit."""
        # Create very long text
        text = " ".join(["word" for _ in range(2000)])

        windows = selector.select_windows(text)

        # All windows should be under limit
        assert all(w["token_count"] <= 512 for w in windows)
