"""Tests for WebReader.

Tests Firecrawl-based web crawling using LlamaIndex SimpleWebPageReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


class TestWebReader:
    """Tests for the WebReader class."""

    def test_web_reader_loads_single_url(self) -> None:
        """Test that WebReader can load a single URL."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com", limit=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].text is not None
        assert len(docs[0].text) > 0
        assert docs[0].metadata["source_url"] == "https://example.com"

    def test_web_reader_respects_limit(self) -> None:
        """Test that WebReader respects the limit parameter."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com/docs", limit=3)

        assert len(docs) <= 3

    def test_web_reader_validates_url_format(self) -> None:
        """Test that WebReader validates URL format."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")

        with pytest.raises(ValueError, match="Invalid URL"):
            reader.load_data(url="not-a-url", limit=1)

    def test_web_reader_handles_empty_url(self) -> None:
        """Test that WebReader rejects empty URLs."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")

        with pytest.raises(ValueError, match="URL"):
            reader.load_data(url="", limit=1)

    def test_web_reader_requires_firecrawl_url(self) -> None:
        """Test that WebReader requires firecrawl_url parameter."""
        from packages.ingest.readers.web import WebReader

        with pytest.raises(TypeError):
            WebReader()  # Missing required firecrawl_url

    def test_web_reader_returns_document_list(self) -> None:
        """Test that WebReader returns a list of Document objects."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://taboot-crawler:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com", limit=1)

        assert isinstance(docs, list)
        assert all(isinstance(doc, Document) for doc in docs)

    def test_web_reader_includes_location_in_params(self) -> None:
        """Test that WebReader includes location parameter for language control.

        Firecrawl v2 supports location parameter to control language/locale:
        - location.country: ISO country code (e.g., 'US')
        - location.languages: Array of locale codes (e.g., ['en-US'])

        This prevents auto-redirects to non-English locales.
        """
        from packages.ingest.readers.web import WebReader
        from unittest.mock import patch, MagicMock

        # Mock FireCrawlWebReader to inspect params
        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            # Create WebReader with config
            web_reader = WebReader(
                firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
            )

            # Call load_data (which creates FireCrawlWebReader with params)
            web_reader.load_data("https://example.com", limit=5)

            # Verify FireCrawlWebReader was called with location parameter
            mock_reader_class.assert_called_once()
            call_kwargs = mock_reader_class.call_args[1]

            assert "params" in call_kwargs, "params should be passed to FireCrawlWebReader"
            params = call_kwargs["params"]

            assert "scrape_options" in params, "scrape_options should be in params"
            scrape_options = params["scrape_options"]

            assert "location" in scrape_options, "location should be in scrape_options"
            location = scrape_options["location"]

            # Verify location structure
            assert "country" in location, "country should be in location"
            assert "languages" in location, "languages should be in location"
            assert isinstance(location["languages"], list), "languages should be a list"

            # Verify default values (should be en-US)
            assert location["country"] == "US", "default country should be US"
            assert "en-US" in location["languages"], "en-US should be in languages"

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
