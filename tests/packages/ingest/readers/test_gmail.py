"""Tests for GmailReader.

Tests Gmail message ingestion using LlamaIndex GmailReader.
Following TDD methodology (RED-GREEN-REFACTOR).

Phase 4 Integration Test: Verify GmailReader extracts new entity types.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from llama_index.core import Document

from packages.schemas.gmail import Attachment, Email, GmailLabel, Thread


class TestGmailReader:
    """Tests for the GmailReader class."""

    def test_gmail_reader_loads_messages(self) -> None:
        """Test that GmailReader can load Gmail messages."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=10)

        assert isinstance(docs, list)
        assert len(docs) <= 10
        assert all(isinstance(doc, Document) for doc in docs)

    def test_gmail_reader_validates_credentials_path(self) -> None:
        """Test that GmailReader validates credentials path."""
        from packages.ingest.readers.gmail import GmailReader

        with pytest.raises(ValueError, match="credentials_path"):
            GmailReader(credentials_path="")

    def test_gmail_reader_handles_empty_query(self) -> None:
        """Test that GmailReader allows empty query (all messages)."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        # Empty query should not raise error
        docs = reader.load_data(query="", limit=1)
        assert isinstance(docs, list)

    def test_gmail_reader_respects_limit(self) -> None:
        """Test that GmailReader respects the limit parameter."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=5)

        assert len(docs) <= 5

    def test_gmail_reader_includes_metadata(self) -> None:
        """Test that GmailReader includes email metadata."""
        from packages.ingest.readers.gmail import GmailReader

        reader = GmailReader(credentials_path="/path/to/credentials.json")
        docs = reader.load_data(query="is:unread", limit=1)

        if docs:
            assert docs[0].metadata is not None
            assert "source_type" in docs[0].metadata
            assert docs[0].metadata["source_type"] == "gmail"


class TestGmailReaderEntityExtraction:
    """Integration tests for GmailReader extracting new entity types (T201).

    Tests that GmailReader properly extracts:
    - Email entities
    - Thread entities
    - GmailLabel entities
    - Attachment entities

    Following the pattern from Phase 4 refactor.
    """

    @pytest.fixture
    def mock_gmail_service(self) -> Mock:
        """Create mock Gmail API service with test data."""
        mock_service = Mock()

        # Mock message data structure (simplified Gmail API response)
        mock_message = {
            "id": "msg_12345",
            "threadId": "thread_67890",
            "labelIds": ["INBOX", "IMPORTANT", "Label_1"],
            "snippet": "Thanks for the update...",
            "internalDate": "1705315800000",  # 2024-01-15T10:30:00Z in ms
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Re: Project Update"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:30:00 +0000"},
                    {"name": "In-Reply-To", "value": "<msg_11111@example.com>"},
                    {"name": "References", "value": "<msg_11111@example.com> <msg_11112@example.com>"},
                ],
                "body": {
                    "size": 2048,
                    "data": "RnVsbCBlbWFpbCBib2R5IGNvbnRlbnQ=",  # base64: "Full email body content"
                },
                "parts": [
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {
                            "attachmentId": "attach_12345",
                            "size": 2048000,
                        },
                    },
                    {
                        "filename": "logo.png",
                        "mimeType": "image/png",
                        "body": {
                            "attachmentId": "attach_img_001",
                            "size": 50000,
                        },
                        "headers": [
                            {"name": "Content-Disposition", "value": "inline"},
                        ],
                    },
                ],
            },
            "sizeEstimate": 2100000,
        }

        # Mock thread data
        mock_thread = {
            "id": "thread_67890",
            "messages": [mock_message] * 3,  # Simulate 3 messages in thread
        }

        # Mock labels
        mock_labels = [
            {
                "id": "INBOX",
                "name": "INBOX",
                "type": "system",
                "messagesTotal": 150,
            },
            {
                "id": "IMPORTANT",
                "name": "IMPORTANT",
                "type": "system",
                "messagesTotal": 42,
            },
            {
                "id": "Label_1",
                "name": "Work Projects",
                "type": "user",
                "color": {"backgroundColor": "#ff0000"},
                "messagesTotal": 25,
            },
        ]

        # Configure mock service methods
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_12345", "threadId": "thread_67890"}],
        }
        mock_service.users().messages().get().execute.return_value = mock_message
        mock_service.users().threads().get().execute.return_value = mock_thread
        mock_service.users().labels().list().execute.return_value = {"labels": mock_labels}

        return mock_service

    def test_extract_email_entities_from_messages(self, mock_gmail_service: Mock) -> None:
        """Test extracting Email entities from Gmail API messages.

        Verifies:
        - Email entity creation with all required fields
        - Temporal tracking (created_at, updated_at, source_timestamp)
        - Extraction metadata (tier A, method, confidence, version)
        - Content fields (message_id, thread_id, subject, body, snippet)
        - Metadata fields (labels, size_estimate, has_attachments)
        - Thread fields (in_reply_to, references)
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")

            # Call new extract_entities method (to be implemented)
            entities = reader.extract_entities(query="is:unread", limit=1)

            # Verify Email entities were extracted
            emails = [e for e in entities if isinstance(e, Email)]
            assert len(emails) > 0, "Should extract at least one Email entity"

            email = emails[0]

            # Identity fields
            assert email.message_id == "msg_12345"
            assert email.thread_id == "thread_67890"

            # Content fields
            assert email.subject == "Re: Project Update"
            assert email.snippet == "Thanks for the update..."
            assert email.body is not None
            assert len(email.body) > 0

            # Metadata fields
            assert "INBOX" in email.labels
            assert "IMPORTANT" in email.labels
            assert email.size_estimate > 0
            assert email.has_attachments is True

            # Thread fields
            assert email.in_reply_to == "msg_11111@example.com"
            assert len(email.references) == 2
            assert "msg_11111@example.com" in email.references

            # Temporal tracking
            assert email.created_at is not None
            assert email.updated_at is not None
            assert email.source_timestamp is not None
            assert email.sent_at is not None

            # Extraction metadata
            assert email.extraction_tier == "A"
            assert email.extraction_method == "gmail_api"
            assert email.confidence == 1.0
            assert email.extractor_version is not None

    def test_extract_thread_entities_from_conversations(self, mock_gmail_service: Mock) -> None:
        """Test extracting Thread entities from Gmail conversations.

        Verifies:
        - Thread entity creation with statistics
        - Message count and participant count
        - First/last message timestamps
        - Label aggregation from thread messages
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            # Verify Thread entities were extracted
            threads = [e for e in entities if isinstance(e, Thread)]
            assert len(threads) > 0, "Should extract at least one Thread entity"

            thread = threads[0]

            # Identity field
            assert thread.thread_id == "thread_67890"

            # Content field
            assert thread.subject == "Re: Project Update"

            # Statistics fields
            assert thread.message_count >= 1
            assert thread.participant_count >= 1

            # Timeline fields
            assert thread.first_message_at is not None
            assert thread.last_message_at is not None
            assert thread.first_message_at <= thread.last_message_at

            # Metadata fields
            assert len(thread.labels) > 0
            assert "INBOX" in thread.labels

            # Temporal tracking
            assert thread.created_at is not None
            assert thread.updated_at is not None

            # Extraction metadata
            assert thread.extraction_tier == "A"
            assert thread.extraction_method == "gmail_api"
            assert thread.confidence == 1.0

    def test_extract_gmail_label_entities(self, mock_gmail_service: Mock) -> None:
        """Test extracting GmailLabel entities from label list.

        Verifies:
        - System labels (INBOX, SENT, etc.)
        - User labels with color metadata
        - Message counts per label
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            # Verify GmailLabel entities were extracted
            labels = [e for e in entities if isinstance(e, GmailLabel)]
            assert len(labels) >= 3, "Should extract at least 3 labels (INBOX, IMPORTANT, Label_1)"

            # Find system label
            inbox_label = next((l for l in labels if l.label_id == "INBOX"), None)
            assert inbox_label is not None
            assert inbox_label.name == "INBOX"
            assert inbox_label.type == "system"
            assert inbox_label.message_count == 150

            # Find user label
            user_label = next((l for l in labels if l.label_id == "Label_1"), None)
            assert user_label is not None
            assert user_label.name == "Work Projects"
            assert user_label.type == "user"
            assert user_label.color == "#ff0000"
            assert user_label.message_count == 25

            # Verify temporal tracking
            for label in labels:
                assert label.created_at is not None
                assert label.updated_at is not None
                assert label.extraction_tier == "A"
                assert label.extraction_method == "gmail_api"

    def test_extract_attachment_entities(self, mock_gmail_service: Mock) -> None:
        """Test extracting Attachment entities from email parts.

        Verifies:
        - Regular attachments (PDFs, docs)
        - Inline attachments (images)
        - Attachment metadata (filename, mime_type, size)
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            # Verify Attachment entities were extracted
            attachments = [e for e in entities if isinstance(e, Attachment)]
            assert len(attachments) >= 2, "Should extract at least 2 attachments"

            # Find regular attachment (PDF)
            pdf_attachment = next((a for a in attachments if a.filename == "report.pdf"), None)
            assert pdf_attachment is not None
            assert pdf_attachment.attachment_id == "attach_12345"
            assert pdf_attachment.mime_type == "application/pdf"
            assert pdf_attachment.size == 2048000
            assert pdf_attachment.is_inline is False

            # Find inline attachment (image)
            img_attachment = next((a for a in attachments if a.filename == "logo.png"), None)
            assert img_attachment is not None
            assert img_attachment.attachment_id == "attach_img_001"
            assert img_attachment.mime_type == "image/png"
            assert img_attachment.size == 50000
            assert img_attachment.is_inline is True

            # Verify temporal tracking
            for attachment in attachments:
                assert attachment.created_at is not None
                assert attachment.updated_at is not None
                assert attachment.extraction_tier == "A"
                assert attachment.extraction_method == "gmail_api"

    def test_extract_entities_returns_all_types(self, mock_gmail_service: Mock) -> None:
        """Test that extract_entities returns all entity types in one call.

        Verifies comprehensive extraction:
        - Email entities (messages)
        - Thread entities (conversations)
        - GmailLabel entities (labels)
        - Attachment entities (from message parts)
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            # Count entity types
            email_count = sum(1 for e in entities if isinstance(e, Email))
            thread_count = sum(1 for e in entities if isinstance(e, Thread))
            label_count = sum(1 for e in entities if isinstance(e, GmailLabel))
            attachment_count = sum(1 for e in entities if isinstance(e, Attachment))

            # Verify all types present
            assert email_count > 0, "Should extract Email entities"
            assert thread_count > 0, "Should extract Thread entities"
            assert label_count > 0, "Should extract GmailLabel entities"
            assert attachment_count > 0, "Should extract Attachment entities"

            # Verify total count
            assert len(entities) == email_count + thread_count + label_count + attachment_count

    def test_extract_entities_handles_no_attachments(self, mock_gmail_service: Mock) -> None:
        """Test extraction when messages have no attachments."""
        from packages.ingest.readers.gmail import GmailReader

        # Mock message without attachments
        mock_message_no_attach = {
            "id": "msg_99999",
            "threadId": "thread_99999",
            "labelIds": ["INBOX"],
            "snippet": "Simple message without attachments",
            "internalDate": "1705315800000",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Simple Email"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:30:00 +0000"},
                ],
                "body": {
                    "size": 100,
                    "data": "U2ltcGxlIGJvZHk=",  # base64: "Simple body"
                },
            },
            "sizeEstimate": 100,
        }

        mock_gmail_service.users().messages().get().execute.return_value = mock_message_no_attach

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="", limit=1)

            # Verify no Attachment entities
            attachments = [e for e in entities if isinstance(e, Attachment)]
            assert len(attachments) == 0, "Should not extract attachments when none exist"

            # Verify Email entity shows has_attachments=False
            emails = [e for e in entities if isinstance(e, Email)]
            if emails:
                assert emails[0].has_attachments is False

    def test_extract_entities_validates_temporal_tracking(self, mock_gmail_service: Mock) -> None:
        """Test that all extracted entities have proper temporal tracking.

        Ensures:
        - created_at and updated_at are set
        - source_timestamp is populated when available
        - Timestamps are valid datetime objects
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            for entity in entities:
                # All entities must have temporal tracking
                assert hasattr(entity, "created_at"), f"{type(entity).__name__} missing created_at"
                assert hasattr(entity, "updated_at"), f"{type(entity).__name__} missing updated_at"
                assert entity.created_at is not None
                assert entity.updated_at is not None
                assert isinstance(entity.created_at, datetime)
                assert isinstance(entity.updated_at, datetime)

                # source_timestamp may be None for some entities (e.g., labels)
                if hasattr(entity, "source_timestamp") and entity.source_timestamp is not None:
                    assert isinstance(entity.source_timestamp, datetime)

    def test_extract_entities_validates_extraction_metadata(self, mock_gmail_service: Mock) -> None:
        """Test that all entities have proper extraction metadata.

        Ensures:
        - extraction_tier is "A" (deterministic Gmail API extraction)
        - extraction_method is "gmail_api"
        - confidence is 1.0 (Tier A has perfect confidence)
        - extractor_version is set
        """
        from packages.ingest.readers.gmail import GmailReader

        with patch("packages.ingest.readers.gmail.build") as mock_build:
            mock_build.return_value = mock_gmail_service

            reader = GmailReader(credentials_path="/path/to/credentials.json")
            entities = reader.extract_entities(query="is:unread", limit=1)

            for entity in entities:
                assert entity.extraction_tier == "A", "Gmail API extraction is Tier A (deterministic)"
                assert entity.extraction_method == "gmail_api", "Method should be gmail_api"
                assert entity.confidence == 1.0, "Tier A has perfect confidence"
                assert entity.extractor_version is not None, "Version should be set"
                assert len(entity.extractor_version) > 0
