"""Unit tests for Gmail reader."""

from unittest.mock import MagicMock, patch

import pytest

from llamacrawl.readers.gmail import GmailReader


@pytest.mark.unit
@pytest.mark.gmail
class TestGmailReader:
    """Test Gmail reader functionality."""

    @pytest.fixture
    def gmail_config(self) -> dict[str, any]:
        """Provide Gmail source configuration."""
        return {
            "labels": ["INBOX", "SENT"],
            "max_results": 500,
            "include_attachments_metadata": True,
        }

    @pytest.fixture
    def gmail_reader(self, gmail_config: dict[str, any]) -> GmailReader:
        """Create Gmail reader instance."""
        with patch("googleapiclient.discovery.build"):
            mock_redis = MagicMock()
            reader = GmailReader(
                source_name="gmail",
                config=gmail_config,
                redis_client=mock_redis,
            )
            reader._gmail_service = MagicMock()
            return reader

    def test_build_query_no_cursor(self, gmail_reader: GmailReader) -> None:
        """Test query building without cursor (first sync)."""
        with patch.object(gmail_reader, "get_last_cursor", return_value=None):
            query = gmail_reader._build_query(["INBOX", "SENT"])
            assert query == "(label:INBOX OR label:SENT)"

    def test_build_query_with_cursor(self, gmail_reader: GmailReader) -> None:
        """Test query building with cursor (incremental sync)."""
        with patch.object(gmail_reader, "get_last_cursor", return_value="2025/10/01"):
            query = gmail_reader._build_query(["INBOX"])
            assert query == "after:2025/10/01 label:INBOX"

    def test_build_query_ignore_cursor(self, gmail_reader: GmailReader) -> None:
        """Test query building with ignore_cursor=True."""
        with patch.object(gmail_reader, "get_last_cursor", return_value="2025/10/01"):
            query = gmail_reader._build_query(["INBOX", "SENT"], ignore_cursor=True)
            assert query == "(label:INBOX OR label:SENT)"

    def test_build_query_single_label(self, gmail_reader: GmailReader) -> None:
        """Test query building with single label."""
        with patch.object(gmail_reader, "get_last_cursor", return_value=None):
            query = gmail_reader._build_query(["INBOX"])
            assert query == "label:INBOX"

    def test_build_query_multiple_labels_with_cursor(self, gmail_reader: GmailReader) -> None:
        """Test query building with multiple labels and cursor."""
        with patch.object(gmail_reader, "get_last_cursor", return_value="2024/12/31"):
            query = gmail_reader._build_query(["INBOX", "SENT", "DRAFT"])
            assert query == "after:2024/12/31 (label:INBOX OR label:SENT OR label:DRAFT)"


@pytest.mark.unit
class TestGmailQueryBuilder:
    """Test Gmail query building edge cases."""

    @pytest.fixture
    def reader(self) -> GmailReader:
        """Create minimal Gmail reader."""
        with patch("googleapiclient.discovery.build"):
            mock_redis = MagicMock()
            return GmailReader(
                source_name="test",
                config={"labels": ["INBOX"]},
                redis_client=mock_redis,
            )

    def test_empty_labels_fallback(self, reader: GmailReader) -> None:
        """Test query defaults to INBOX when no labels provided."""
        with patch.object(reader, "get_last_cursor", return_value=None):
            query = reader._build_query([])
            assert query == "label:INBOX"

    def test_cursor_format(self, reader: GmailReader) -> None:
        """Test cursor uses YYYY/MM/DD format for Gmail compatibility."""
        with patch.object(reader, "get_last_cursor", return_value="2025/10/02"):
            query = reader._build_query(["INBOX"])
            assert "after:2025/10/02" in query
            # Ensure no other date formats
            assert "after:2025-10-02" not in query
            assert "after:20251002" not in query
