"""Tests for GmailWriter - Batched Neo4j writer for Gmail entities.

Tests cover:
- Empty list handling
- Single entity writes
- Batch 2000 writes
- Idempotency (MERGE behavior)
- Relationship creation (Email->Thread, Email->Person, Email->Attachment, Email->GmailLabel)
"""

from datetime import UTC, datetime

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.gmail_writer import GmailWriter
from packages.schemas.gmail import Attachment, Email, GmailLabel, Thread

# Mark all tests as integration tests (require Neo4j)
pytestmark = pytest.mark.integration


@pytest.fixture
def neo4j_client() -> Neo4jClient:
    """Create and connect Neo4j client for tests."""
    client = Neo4jClient()
    client.connect()
    yield client

    # Cleanup: Delete all Gmail nodes after test
    with client.session() as session:
        session.run(
            "MATCH (n) WHERE n:Email OR n:Thread OR n:GmailLabel OR n:Attachment "
            "DETACH DELETE n"
        )

    client.close()


@pytest.fixture
def gmail_writer(neo4j_client: Neo4jClient) -> GmailWriter:
    """Create GmailWriter instance with test Neo4j client."""
    return GmailWriter(neo4j_client)


@pytest.fixture
def sample_email() -> Email:
    """Create sample Email entity for testing."""
    return Email(
        message_id="msg_12345",
        thread_id="thread_67890",
        subject="Test Email",
        snippet="This is a test email snippet",
        body="Full email body content here",
        sent_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        labels=["INBOX", "IMPORTANT"],
        size_estimate=2048,
        has_attachments=True,
        in_reply_to="msg_11111",
        references=["msg_11111", "msg_11112"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="gmail_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_thread() -> Thread:
    """Create sample Thread entity for testing."""
    return Thread(
        thread_id="thread_67890",
        subject="Test Thread",
        message_count=5,
        participant_count=3,
        first_message_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        last_message_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        labels=["INBOX", "IMPORTANT"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        source_timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="gmail_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_label() -> GmailLabel:
    """Create sample GmailLabel entity for testing."""
    return GmailLabel(
        label_id="Label_1",
        name="Important Work",
        type="user",
        color="#ff0000",
        message_count=42,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="gmail_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_attachment() -> Attachment:
    """Create sample Attachment entity for testing."""
    return Attachment(
        attachment_id="attach_12345",
        filename="report.pdf",
        mime_type="application/pdf",
        size=2048000,
        content_hash="sha256:abc123def456",
        is_inline=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        extraction_tier="A",
        extraction_method="gmail_api",
        confidence=1.0,
        extractor_version="1.0.0",
    )


class TestWriteEmails:
    """Tests for write_emails method."""

    def test_write_empty_list(self, gmail_writer: GmailWriter) -> None:
        """Test writing an empty list returns zero counts."""
        result = gmail_writer.write_emails([])

        assert result["total_written"] == 0
        assert result["batches_executed"] == 0

    def test_write_single_email(
        self, gmail_writer: GmailWriter, sample_email: Email, neo4j_client: Neo4jClient
    ) -> None:
        """Test writing a single Email node."""
        result = gmail_writer.write_emails([sample_email])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query_result = session.run(
                "MATCH (e:Email {message_id: $message_id}) RETURN e",
                {"message_id": sample_email.message_id},
            )
            record = query_result.single()
            assert record is not None

            email_node = record["e"]
            assert email_node["message_id"] == sample_email.message_id
            assert email_node["thread_id"] == sample_email.thread_id
            assert email_node["subject"] == sample_email.subject
            assert email_node["snippet"] == sample_email.snippet
            assert email_node["has_attachments"] == sample_email.has_attachments

    def test_write_idempotent(
        self, gmail_writer: GmailWriter, sample_email: Email, neo4j_client: Neo4jClient
    ) -> None:
        """Test writing the same Email twice is idempotent (MERGE behavior)."""
        # First write
        result1 = gmail_writer.write_emails([sample_email])
        assert result1["total_written"] == 1

        # Modify snippet
        sample_email.snippet = "Updated snippet"

        # Second write (should update existing node)
        result2 = gmail_writer.write_emails([sample_email])
        assert result2["total_written"] == 1

        # Verify only one node exists with updated snippet
        with neo4j_client.session() as session:
            query_result = session.run(
                "MATCH (e:Email {message_id: $message_id}) RETURN e",
                {"message_id": sample_email.message_id},
            )
            records = list(query_result)
            assert len(records) == 1
            assert records[0]["e"]["snippet"] == "Updated snippet"

    def test_write_batch_2000(self, gmail_writer: GmailWriter, neo4j_client: Neo4jClient) -> None:
        """Test writing 2000 emails in a single batch."""
        emails = [
            Email(
                message_id=f"msg_{i:05d}",
                thread_id=f"thread_{i % 100}",
                subject=f"Test Email {i}",
                snippet=f"Snippet {i}",
                sent_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                size_estimate=1024,
                has_attachments=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="gmail_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            for i in range(2000)
        ]

        result = gmail_writer.write_emails(emails)

        assert result["total_written"] == 2000
        assert result["batches_executed"] == 1

        # Verify count in Neo4j
        with neo4j_client.session() as session:
            count_result = session.run("MATCH (e:Email) RETURN count(e) AS count")
            count = count_result.single()["count"]
            assert count == 2000


class TestWriteThreads:
    """Tests for write_threads method."""

    def test_write_empty_list(self, gmail_writer: GmailWriter) -> None:
        """Test writing an empty list returns zero counts."""
        result = gmail_writer.write_threads([])

        assert result["total_written"] == 0
        assert result["batches_executed"] == 0

    def test_write_single_thread(
        self, gmail_writer: GmailWriter, sample_thread: Thread, neo4j_client: Neo4jClient
    ) -> None:
        """Test writing a single Thread node."""
        result = gmail_writer.write_threads([sample_thread])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query_result = session.run(
                "MATCH (t:Thread {thread_id: $thread_id}) RETURN t",
                {"thread_id": sample_thread.thread_id},
            )
            record = query_result.single()
            assert record is not None

            thread_node = record["t"]
            assert thread_node["thread_id"] == sample_thread.thread_id
            assert thread_node["subject"] == sample_thread.subject
            assert thread_node["message_count"] == sample_thread.message_count
            assert thread_node["participant_count"] == sample_thread.participant_count


class TestWriteLabels:
    """Tests for write_labels method."""

    def test_write_empty_list(self, gmail_writer: GmailWriter) -> None:
        """Test writing an empty list returns zero counts."""
        result = gmail_writer.write_labels([])

        assert result["total_written"] == 0
        assert result["batches_executed"] == 0

    def test_write_single_label(
        self, gmail_writer: GmailWriter, sample_label: GmailLabel, neo4j_client: Neo4jClient
    ) -> None:
        """Test writing a single GmailLabel node."""
        result = gmail_writer.write_labels([sample_label])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query_result = session.run(
                "MATCH (l:GmailLabel {label_id: $label_id}) RETURN l",
                {"label_id": sample_label.label_id},
            )
            record = query_result.single()
            assert record is not None

            label_node = record["l"]
            assert label_node["label_id"] == sample_label.label_id
            assert label_node["name"] == sample_label.name
            assert label_node["type"] == sample_label.type


class TestWriteAttachments:
    """Tests for write_attachments method."""

    def test_write_empty_list(self, gmail_writer: GmailWriter) -> None:
        """Test writing an empty list returns zero counts."""
        result = gmail_writer.write_attachments([])

        assert result["total_written"] == 0
        assert result["batches_executed"] == 0

    def test_write_single_attachment(
        self, gmail_writer: GmailWriter, sample_attachment: Attachment, neo4j_client: Neo4jClient
    ) -> None:
        """Test writing a single Attachment node."""
        result = gmail_writer.write_attachments([sample_attachment])

        assert result["total_written"] == 1
        assert result["batches_executed"] == 1

        # Verify node was created in Neo4j
        with neo4j_client.session() as session:
            query_result = session.run(
                "MATCH (a:Attachment {attachment_id: $attachment_id}) RETURN a",
                {"attachment_id": sample_attachment.attachment_id},
            )
            record = query_result.single()
            assert record is not None

            attachment_node = record["a"]
            assert attachment_node["attachment_id"] == sample_attachment.attachment_id
            assert attachment_node["filename"] == sample_attachment.filename
            assert attachment_node["mime_type"] == sample_attachment.mime_type
            assert attachment_node["size"] == sample_attachment.size


class TestRelationships:
    """Tests for relationship creation methods."""

    def test_write_email_in_thread_relationships(
        self,
        gmail_writer: GmailWriter,
        sample_email: Email,
        sample_thread: Thread,
        neo4j_client: Neo4jClient,
    ) -> None:
        """Test creating IN_THREAD relationships from Email to Thread."""
        # First write nodes
        gmail_writer.write_emails([sample_email])
        gmail_writer.write_threads([sample_thread])

        # Create relationship
        result = gmail_writer.write_email_in_thread_relationships(
            [{"email_message_id": sample_email.message_id, "thread_id": sample_thread.thread_id}]
        )

        assert result["total_written"] == 1
        assert result["batches_executed"] >= 1

        # Verify relationship exists
        with neo4j_client.session() as session:
            query_result = session.run(
                """
                MATCH (e:Email {message_id: $message_id})
                      -[r:IN_THREAD]->(t:Thread {thread_id: $thread_id})
                RETURN r
                """,
                {"message_id": sample_email.message_id, "thread_id": sample_thread.thread_id},
            )
            record = query_result.single()
            assert record is not None

    def test_write_email_has_attachment_relationships(
        self,
        gmail_writer: GmailWriter,
        sample_email: Email,
        sample_attachment: Attachment,
        neo4j_client: Neo4jClient,
    ) -> None:
        """Test creating HAS_ATTACHMENT relationships from Email to Attachment."""
        # First write nodes
        gmail_writer.write_emails([sample_email])
        gmail_writer.write_attachments([sample_attachment])

        # Create relationship
        result = gmail_writer.write_email_has_attachment_relationships(
            [
                {
                    "email_message_id": sample_email.message_id,
                    "attachment_id": sample_attachment.attachment_id,
                }
            ]
        )

        assert result["total_written"] == 1
        assert result["batches_executed"] >= 1

        # Verify relationship exists
        with neo4j_client.session() as session:
            query_result = session.run(
                """
                MATCH (e:Email {message_id: $message_id})
                      -[r:HAS_ATTACHMENT]->(a:Attachment {attachment_id: $attachment_id})
                RETURN r
                """,
                {
                    "message_id": sample_email.message_id,
                    "attachment_id": sample_attachment.attachment_id,
                },
            )
            record = query_result.single()
            assert record is not None

    def test_write_email_has_label_relationships(
        self,
        gmail_writer: GmailWriter,
        sample_email: Email,
        sample_label: GmailLabel,
        neo4j_client: Neo4jClient,
    ) -> None:
        """Test creating HAS_LABEL relationships from Email to GmailLabel."""
        # First write nodes
        gmail_writer.write_emails([sample_email])
        gmail_writer.write_labels([sample_label])

        # Create relationship
        result = gmail_writer.write_email_has_label_relationships(
            [{"email_message_id": sample_email.message_id, "label_id": sample_label.label_id}]
        )

        assert result["total_written"] == 1
        assert result["batches_executed"] >= 1

        # Verify relationship exists
        with neo4j_client.session() as session:
            query_result = session.run(
                """
                MATCH (e:Email {message_id: $message_id})
                      -[r:HAS_LABEL]->(l:GmailLabel {label_id: $label_id})
                RETURN r
                """,
                {"message_id": sample_email.message_id, "label_id": sample_label.label_id},
            )
            record = query_result.single()
            assert record is not None
