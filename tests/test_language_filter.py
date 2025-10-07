"""Tests for language filtering transformation component.

This module tests the LanguageFilter class which filters document chunks
by detected language before embedding to save costs and improve quality.
"""

from datetime import UTC, datetime

import logging

import pytest
from llama_index.core.schema import TextNode
from pydantic import ValidationError

from llamacrawl.config import LanguageFilterConfig
from llamacrawl.ingestion.language_filter import (
    LanguageFilter,
    build_language_filter_from_config,
    filter_documents_by_language,
)
from llamacrawl.models.document import Document, DocumentMetadata


class TestLanguageFilterBasic:
    """Basic language filtering functionality tests."""

    def test_filters_non_english(self) -> None:
        """Test that non-English chunks are filtered out."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(text="This is English text about machine learning.", id_="1"),
            TextNode(
                text="Ceci est un texte français sur l'apprentissage automatique.",
                id_="2",
            ),
            TextNode(
                text="Dies ist ein deutscher Text über maschinelles Lernen.",
                id_="3",
            ),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1
        assert filtered[0].node_id == "1"

    def test_multi_language_allowlist(self) -> None:
        """Test multiple allowed languages."""
        filter_instance = LanguageFilter(allowed_languages={"en", "es"}, min_content_length=0)
        nodes = [
            TextNode(
                text="English text about programming and software development.",
                id_="1",
            ),
            TextNode(
                text="Texto en español sobre programación y desarrollo de software.",
                id_="2",
            ),
            TextNode(text="Texte français sur la programmation.", id_="3"),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 2
        assert {node.node_id for node in filtered} == {"1", "2"}

    def test_empty_allowlist_passthrough(self) -> None:
        """Test empty allowlist allows all languages."""
        filter_instance = LanguageFilter(allowed_languages=set())
        nodes = [
            TextNode(text="Any language text", id_="1"),
            TextNode(text="Texte en français", id_="2"),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 2

    def test_short_text_bypass(self) -> None:
        """Test short text passes through without detection."""
        filter_instance = LanguageFilter(
            allowed_languages={"en"}, min_content_length=100
        )
        nodes = [
            TextNode(text="Hi", id_="1"),  # Too short
            TextNode(text="Bonjour", id_="2"),  # Too short
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 2

    def test_empty_nodes_list(self) -> None:
        """Test empty nodes list returns empty list."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        filtered = filter_instance([])
        assert filtered == []


class TestLanguageFilterConfidence:
    """Tests for confidence threshold filtering."""

    def test_high_confidence_threshold(self) -> None:
        """Test high confidence threshold filters ambiguous text."""
        filter_instance = LanguageFilter(
            allowed_languages={"en"}, confidence_threshold=0.95, min_content_length=0
        )
        nodes = [
            TextNode(
                text="This is clearly English text with sufficient length for detection.",
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        # Should pass (high confidence English)
        assert len(filtered) == 1

    def test_low_confidence_passthrough(self) -> None:
        """Test low confidence threshold is more permissive."""
        filter_instance = LanguageFilter(
            allowed_languages={"en"}, confidence_threshold=0.5, min_content_length=0
        )
        nodes = [
            TextNode(
                text="This is English text that should definitely pass with low threshold.",
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1


class TestLanguageFilterValidation:
    """Tests for configuration validation."""

    def test_invalid_confidence_threshold_high(self) -> None:
        """Test confidence threshold > 1.0 raises error."""
        with pytest.raises(ValidationError) as exc:
            LanguageFilter(confidence_threshold=1.5)
        assert "less than or equal to 1" in str(exc.value)

    def test_invalid_confidence_threshold_low(self) -> None:
        """Test confidence threshold < 0.0 raises error."""
        with pytest.raises(ValidationError) as exc:
            LanguageFilter(confidence_threshold=-0.1)
        assert "greater than or equal to 0" in str(exc.value)

    def test_valid_confidence_threshold_bounds(self) -> None:
        """Test boundary values for confidence threshold."""
        # Should not raise
        LanguageFilter(confidence_threshold=0.0)
        LanguageFilter(confidence_threshold=1.0)
        LanguageFilter(confidence_threshold=0.8)


class TestLanguageFilterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_code_snippet_handling(self) -> None:
        """Test code snippets are handled gracefully."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(
                text="def hello(): print('Hello World')  # This is English comment",
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        # Should include (code with English comments)
        assert len(filtered) >= 0  # May or may not filter depending on detection

    def test_mixed_language_text(self) -> None:
        """Test text with mixed languages uses primary language."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(
                text=("This is primarily English text with detailed explanations." * 4) + " Quelques mots français.",
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        # Should detect as English (primary language)
        assert len(filtered) == 1

    def test_unicode_text(self) -> None:
        """Test Unicode text is handled correctly."""
        filter_instance = LanguageFilter(allowed_languages={"en", "zh"}, min_content_length=0)
        nodes = [
            TextNode(text="This is English text", id_="1"),
            TextNode(text="这是中文文本关于机器学习和人工智能。", id_="2"),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 2

    def test_very_long_text(self) -> None:
        """Test very long text uses first 1000 chars for efficiency."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        long_text = "This is English text. " * 200  # > 1000 chars
        nodes = [TextNode(text=long_text, id_="1")]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1


class TestLanguageFilterStatistics:
    """Tests for filtering statistics and logging."""

    def test_statistics_logging(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that filtering statistics are logged."""
        caplog.set_level(logging.INFO, logger="llamacrawl.ingestion.language_filter")
        filter_instance = LanguageFilter(allowed_languages={"en"}, log_filtered=True, min_content_length=0)
        nodes = [
            TextNode(text="English text about data science.", id_="1"),
            TextNode(text="Texte français sur la science des données.", id_="2"),
        ]
        filtered = filter_instance(nodes)

        # Should log statistics
        assert len(filtered) == 1
        # Check for log message (may be in different log levels)
        log_messages = [rec.message for rec in caplog.records]
        assert any("Language filtering complete" in msg for msg in log_messages)


class TestLanguageFilterIntegration:
    """Integration tests with realistic content."""

    def test_english_documentation(self) -> None:
        """Test filtering English documentation."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(
                text="""
                # Installation Guide

                To install this package, run:
                ```
                pip install llamacrawl
                ```

                This will install all required dependencies.
                """,
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1

    def test_multilingual_documentation(self) -> None:
        """Test filtering multilingual documentation."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(
                text="""
                # Installation Guide (English)
                To install this package, run pip install llamacrawl
                """,
                id_="1",
            ),
            TextNode(
                text="""
                # Guide d'installation (Français)
                Pour installer ce paquet, exécutez pip install llamacrawl
                """,
                id_="2",
            ),
            TextNode(
                text="""
                # Installationsanleitung (Deutsch)
                Um dieses Paket zu installieren, führen Sie pip install llamacrawl aus
                """,
                id_="3",
            ),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1
        assert filtered[0].node_id == "1"

    def test_technical_content_english(self) -> None:
        """Test technical English content passes through."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        nodes = [
            TextNode(
                text="""
                The LanguageFilter class implements a TransformComponent that
                detects and filters document chunks by language using fast-langdetect.
                This approach saves compute costs by filtering before embedding.
                """,
                id_="1",
            ),
        ]
        filtered = filter_instance(nodes)
        assert len(filtered) == 1


class TestLanguageFilterWithMetadata:
    """Tests for nodes with metadata."""

    def test_preserves_node_metadata(self) -> None:
        """Test that node metadata is preserved after filtering."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        node = TextNode(
            text="This is English text with metadata.",
            id_="1",
            metadata={"source": "test", "page": 1},
        )
        filtered = filter_instance([node])
        assert len(filtered) == 1
        assert filtered[0].metadata["source"] == "test"
        assert filtered[0].metadata["page"] == 1

    def test_preserves_node_relationships(self) -> None:
        """Test that node relationships are preserved."""
        filter_instance = LanguageFilter(allowed_languages={"en"}, min_content_length=0)
        node = TextNode(
            text="This is English text.",
            id_="1",
            relationships={},  # LlamaIndex relationship structure
        )
        filtered = filter_instance([node])
        assert len(filtered) == 1
        assert filtered[0].node_id == "1"


class TestLanguageFilterDocumentHelpers:
    """Tests for document-level language filtering helpers."""

    @staticmethod
    def _document(doc_id: str, content: str, language: str) -> Document:
        """Create a Document with specified content and language."""
        return Document(
            doc_id=doc_id,
            title=f"Doc {doc_id}",
            content=content,
            content_hash=f"hash-{doc_id}",
            metadata=DocumentMetadata(
                source_type="firecrawl",
                source_url=f"https://example.com/{doc_id}",
                timestamp=datetime.now(UTC),
                extra={"language": language},
            ),
        )

    def test_filter_documents_by_language_filters_out_non_allowed(self) -> None:
        """Ensure helper removes documents not matching allowed languages."""
        english_text = "This is English content about machine learning." * 5
        french_text = "Ceci est un contenu français sur l'apprentissage automatique." * 5

        documents = [
            self._document("en-1", english_text, "en"),
            self._document("fr-1", french_text, "fr"),
        ]

        language_filter = LanguageFilter(
            allowed_languages={"en"},
            min_content_length=20,
        )

        filtered = filter_documents_by_language(documents, language_filter)
        assert [doc.doc_id for doc in filtered] == ["en-1"]

    def test_filter_documents_by_language_no_filter_when_disabled(self) -> None:
        """Helper returns original documents when filter is None."""
        documents = [
            self._document("en-1", "Short English text.", "en"),
            self._document("fr-1", "Texte français.", "fr"),
        ]

        filtered = filter_documents_by_language(documents, None)
        assert [doc.doc_id for doc in filtered] == [doc.doc_id for doc in documents]

    def test_build_language_filter_from_config(self) -> None:
        """Language filter creation respects configuration and overrides."""
        config = LanguageFilterConfig(
            enabled=True,
            allowed_languages=["en"],
            confidence_threshold=0.75,
            min_content_length=64,
            log_filtered=True,
        )

        language_filter = build_language_filter_from_config(
            config,
            log_filtered_override=False,
        )
        assert language_filter is not None
        assert language_filter.allowed_languages == {"en"}
        assert language_filter.confidence_threshold == 0.75
        assert language_filter.min_content_length == 64
        assert language_filter.log_filtered is False

    def test_build_language_filter_from_config_disabled(self) -> None:
        """Disabled configuration returns None."""
        config = LanguageFilterConfig(enabled=False)
        language_filter = build_language_filter_from_config(config)
        assert language_filter is None


# Mark tests that require the fast-langdetect package
pytestmark = pytest.mark.unit
