"""Tests for WebReader.

Tests Firecrawl-based web crawling using LlamaIndex SimpleWebPageReader.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from llama_index.core import Document


# NOTE: TestParameterNormalization class removed
# The Firecrawl Python SDK expects snake_case parameters (exclude_paths, include_paths)
# and handles conversion to the HTTP API format internally. No normalization needed in WebReader.


class TestWebReader:
    """Tests for the WebReader class."""

    def test_web_reader_loads_single_url(self) -> None:
        """Test that WebReader can load a single URL."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://localhost:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com", limit=1)

        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].text is not None
        assert len(docs[0].text) > 0
        assert docs[0].metadata["source_url"] == "https://example.com"

    def test_web_reader_respects_limit(self) -> None:
        """Test that WebReader respects the limit parameter."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://localhost:3002", firecrawl_api_key="test-key")
        docs = reader.load_data(url="https://example.com/docs", limit=3)

        assert len(docs) <= 3

    def test_web_reader_validates_url_format(self) -> None:
        """Test that WebReader validates URL format."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://localhost:3002", firecrawl_api_key="test-key")

        with pytest.raises(ValueError, match="Invalid URL"):
            reader.load_data(url="not-a-url", limit=1)

    def test_web_reader_handles_empty_url(self) -> None:
        """Test that WebReader rejects empty URLs."""
        from packages.ingest.readers.web import WebReader

        reader = WebReader(firecrawl_url="http://localhost:3002", firecrawl_api_key="test-key")

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

        reader = WebReader(firecrawl_url="http://localhost:3002", firecrawl_api_key="test-key")
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
        from unittest.mock import MagicMock, patch

        from packages.ingest.readers.web import WebReader

        # Mock FireCrawlWebReader to inspect params
        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            # Create WebReader with config
            web_reader = WebReader(firecrawl_url="http://test:3002", firecrawl_api_key="test-key")

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
        """Test that WebReader passes exclude_paths parameter to Firecrawl in camelCase.

        Firecrawl v2 SDK expects snake_case (excludePaths) (SDK handles conversion).
        Patterns match against URL pathname only (not full URL).
        """
        from unittest.mock import MagicMock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            # Create WebReader (config should have default exclude patterns)
            web_reader = WebReader(firecrawl_url="http://test:3002", firecrawl_api_key="test-key")

            # Call load_data
            web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

            # Verify exclude_paths parameter was passed in camelCase
            call_kwargs = mock_reader_class.call_args[1]
            params = call_kwargs["params"]

            # Must be camelCase for Firecrawl v2 API
            assert "exclude_paths" in params, "exclude_paths (snake_case) should be in params"
            assert isinstance(params["exclude_paths"], list), "excludePaths should be a list"
            assert len(params["exclude_paths"]) > 0, "excludePaths should not be empty by default"

    def test_web_reader_passes_include_paths_to_firecrawl(self) -> None:
        """Test that WebReader passes include_paths parameter in camelCase when configured.

        Firecrawl v2 SDK expects snake_case (includePaths) (SDK handles conversion).
        """
        from unittest.mock import MagicMock, Mock, patch

        from packages.ingest.readers.web import WebReader

        # Mock config to return custom includePaths
        # Use patterns that match full URLs for client-side URLFilter validation
        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = "^.*/en/.*$,^.*/docs/.*$"  # Match full URLs
            mock_cfg.firecrawl_exclude_paths = ""
            mock_config.return_value = mock_cfg

            with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
                mock_reader_instance = MagicMock()
                mock_reader_instance.load_data.return_value = []
                mock_reader_class.return_value = mock_reader_instance

                web_reader = WebReader(
                    firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
                )

                web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

                # Verify include_paths parameter (camelCase)
                call_kwargs = mock_reader_class.call_args[1]
                params = call_kwargs["params"]

                assert "include_paths" in params, "include_paths (snake_case) should be in params"
                assert isinstance(params["include_paths"], list), "includePaths should be a list"
                assert len(params["include_paths"]) == 2, "Should have 2 include patterns"
                assert "^.*/en/.*$" in params["include_paths"]
                assert "^.*/docs/.*$" in params["include_paths"]

    def test_web_reader_exclude_paths_defaults_to_common_languages(self) -> None:
        """Test that excludePaths defaults block common non-English languages.

        Default should block: de, fr, es, it, pt, nl, pl, ru, ja, zh, ko, ar, tr, cs, da, sv, no
        """
        from unittest.mock import MagicMock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
            mock_reader_instance = MagicMock()
            mock_reader_instance.load_data.return_value = []
            mock_reader_class.return_value = mock_reader_instance

            web_reader = WebReader(firecrawl_url="http://test:3002", firecrawl_api_key="test-key")

            web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

            call_kwargs = mock_reader_class.call_args[1]
            params = call_kwargs["params"]
            exclude_patterns = params.get("exclude_paths", [])  # Changed to camelCase

            # Verify pattern blocks common languages
            assert len(exclude_patterns) > 0, "Should have default exclude patterns"

            # Check that pattern includes common language codes
            pattern_str = "|".join(exclude_patterns)
            assert "de" in pattern_str or "/de/" in pattern_str, "Should block German"
            assert "fr" in pattern_str or "/fr/" in pattern_str, "Should block French"
            assert "es" in pattern_str or "/es/" in pattern_str, "Should block Spanish"

    def test_web_reader_parses_comma_separated_patterns(self) -> None:
        """Test that WebReader correctly parses comma-separated pattern strings.

        Config values come as comma-separated strings and must be split into lists.
        Also verifies camelCase normalization.
        """
        from unittest.mock import MagicMock, Mock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            # Use patterns that match full URLs for client-side URLFilter validation
            mock_cfg.firecrawl_include_paths = (
                "^.*/en/.*$, ^.*/docs/.*$ , ^.*/api/.*$"  # Whitespace variations
            )
            mock_cfg.firecrawl_exclude_paths = "^.*/de/.*$,^.*/fr/.*$"
            mock_config.return_value = mock_cfg

            with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
                mock_reader_instance = MagicMock()
                mock_reader_instance.load_data.return_value = []
                mock_reader_class.return_value = mock_reader_instance

                web_reader = WebReader(
                    firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
                )

                # Use URL that matches include pattern
                web_reader.load_data("https://example.com/en/docs", limit=5)

                call_kwargs = mock_reader_class.call_args[1]
                params = call_kwargs["params"]

                # Verify parsing with whitespace handling (camelCase keys)
                assert len(params["include_paths"]) == 3, "Should parse 3 include patterns"
                assert "^.*/en/.*$" in params["include_paths"]
                assert "^.*/docs/.*$" in params["include_paths"]
                assert "^.*/api/.*$" in params["include_paths"]

                assert len(params["exclude_paths"]) == 2, "Should parse 2 exclude patterns"
                assert "^.*/de/.*$" in params["exclude_paths"]
                assert "^.*/fr/.*$" in params["exclude_paths"]

    def test_web_reader_empty_patterns_not_included(self) -> None:
        """Test that empty pattern strings don't result in empty list items.

        Handles edge cases like trailing commas or multiple commas.
        """
        from unittest.mock import MagicMock, Mock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = ""  # Test empty patterns handling
            mock_cfg.firecrawl_exclude_paths = "^.*/(de|fr)/.*$,,"  # Trailing commas
            mock_config.return_value = mock_cfg

            with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
                mock_reader_instance = MagicMock()
                mock_reader_instance.load_data.return_value = []
                mock_reader_class.return_value = mock_reader_instance

                web_reader = WebReader(
                    firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
                )

                # URL won't be filtered since we're only testing empty pattern handling
                web_reader.load_data("https://example.com/en/docs", limit=5)

                call_kwargs = mock_reader_class.call_args[1]
                params = call_kwargs["params"]

                # Verify no empty strings in lists (snake_case keys from SDK)
                exclude_paths = params.get("exclude_paths", [])
                for pattern in exclude_paths:
                    assert pattern.strip() != "", "No empty patterns should be in exclude_paths"

                # Verify empty config doesn't add key (snake_case)
                assert "include_paths" not in params or params["include_paths"] == [], (
                    "Empty include_paths config should not add parameter"
                )

    def test_web_reader_rejects_excluded_url_preemptively(self) -> None:
        """Test that WebReader rejects excluded URLs before crawling (defense-in-depth).

        Client-side validation should catch excluded URLs early with clear error messages.
        """
        from unittest.mock import Mock, patch

        from packages.ingest.readers.web import WebReader

        # Mock config with German language exclusion
        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = ""
            mock_cfg.firecrawl_exclude_paths = r"^.*/(de|fr|es)/.*$"
            mock_config.return_value = mock_cfg

            web_reader = WebReader(
                firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
            )

            # Should raise ValueError for excluded URL
            with pytest.raises(ValueError) as exc_info:
                web_reader.load_data("https://docs.anthropic.com/de/docs/intro", limit=5)

            # Verify error message includes pattern info
            error_msg = str(exc_info.value)
            assert "URL rejected by filter" in error_msg
            assert "exclude pattern" in error_msg
            assert "/de/" in error_msg or "de" in error_msg

    def test_web_reader_allows_matching_include_pattern(self) -> None:
        """Test that WebReader allows URLs matching include patterns."""
        from unittest.mock import MagicMock, Mock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = r"^.*/en/.*$"  # Only allow /en/ paths
            mock_cfg.firecrawl_exclude_paths = ""
            mock_config.return_value = mock_cfg

            with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
                mock_reader_instance = MagicMock()
                mock_reader_instance.load_data.return_value = []
                mock_reader_class.return_value = mock_reader_instance

                web_reader = WebReader(
                    firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
                )

                # Should allow /en/ URL
                web_reader.load_data("https://docs.anthropic.com/en/docs", limit=5)

                # Verify FireCrawlWebReader was called (URL was allowed)
                assert mock_reader_class.called

    def test_web_reader_rejects_non_matching_include_pattern(self) -> None:
        """Test that WebReader rejects URLs not matching include patterns."""
        from unittest.mock import Mock, patch

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = r"^.*/en/.*$"  # Only allow /en/ paths
            mock_cfg.firecrawl_exclude_paths = ""
            mock_config.return_value = mock_cfg

            web_reader = WebReader(
                firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
            )

            # Should reject /de/ URL (doesn't match include pattern)
            with pytest.raises(ValueError) as exc_info:
                web_reader.load_data("https://docs.anthropic.com/de/docs", limit=5)

            error_msg = str(exc_info.value)
            assert "does not match any include patterns" in error_msg

    def test_web_reader_post_crawl_filtering(self) -> None:
        """Test that WebReader filters documents after crawl (defense-in-depth).

        Even if Firecrawl returns excluded URLs, client-side filtering should catch them.
        """
        from unittest.mock import MagicMock, Mock, patch

        from llama_index.core import Document

        from packages.ingest.readers.web import WebReader

        with patch("packages.ingest.readers.web.get_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.firecrawl_default_country = "US"
            mock_cfg.firecrawl_default_languages = "en-US"
            mock_cfg.firecrawl_include_paths = ""
            mock_cfg.firecrawl_exclude_paths = r"^.*/(de|fr)/.*$"
            mock_config.return_value = mock_cfg

            with patch("packages.ingest.readers.web.FireCrawlWebReader") as mock_reader_class:
                # Mock returned documents with mixed allowed/excluded URLs
                mock_docs = [
                    Document(
                        text="English doc",
                        metadata={"source_url": "https://example.com/en/docs"},
                    ),
                    Document(
                        text="German doc",
                        metadata={"source_url": "https://example.com/de/docs"},
                    ),
                    Document(
                        text="French doc",
                        metadata={"source_url": "https://example.com/fr/docs"},
                    ),
                    Document(
                        text="Another English doc",
                        metadata={"source_url": "https://example.com/en/api"},
                    ),
                ]

                mock_reader_instance = MagicMock()
                mock_reader_instance.load_data.return_value = mock_docs
                mock_reader_class.return_value = mock_reader_instance

                web_reader = WebReader(
                    firecrawl_url="http://test:3002", firecrawl_api_key="test-key"
                )

                # Load with allowed base URL
                docs = web_reader.load_data("https://example.com/en/docs", limit=10)

                # Verify only English docs are returned (German/French filtered out)
                assert len(docs) == 2, "Should filter out 2 excluded documents"
                assert all("/en/" in doc.metadata["source_url"] for doc in docs)
                assert not any("/de/" in doc.metadata.get("source_url", "") for doc in docs)
                assert not any("/fr/" in doc.metadata.get("source_url", "") for doc in docs)
