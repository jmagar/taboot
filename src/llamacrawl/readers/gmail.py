"""Gmail reader for email ingestion using OAuth 2.0 and Gmail API v1.

This module provides GmailReader for loading emails from a Gmail account.
It uses the Gmail API v1 directly (not LlamaIndex) with OAuth 2.0 credentials
and implements incremental sync using date-based Gmail search operators.

Why Direct API Instead of LlamaIndex:
- LlamaIndex GmailReader requires file-based authentication (credentials.json, token.json)
- Cannot use environment variable credentials without workarounds
- Our implementation follows the same pattern as RedditReader and ElasticsearchReader
- Uses direct API when LlamaIndex readers don't support environment-based auth

OAuth Setup:
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create project and enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Run get_refresh_token() helper to obtain refresh token via OAuth flow
5. Store GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN in .env

Gmail Search Operators (date format: YYYY/MM/DD):
- after:YYYY/MM/DD - emails after date
- before:YYYY/MM/DD - emails before date
- from:email@example.com - from specific sender
- to:email@example.com - to specific recipient
- subject:keyword - subject contains keyword
- label:INBOX - specific label
- has:attachment - has attachments
"""

import base64
import hashlib
import os
from datetime import datetime
from typing import Any

# Note: Not using LlamaIndex GmailReader due to credential handling incompatibility
# We use Gmail API directly instead

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient


class GmailReader(BaseReader):
    """Gmail reader using OAuth 2.0 authentication and Gmail API directly.

    This reader loads emails from Gmail using the Gmail API v1 directly.
    It supports incremental sync via date-based Gmail search queries.

    Attributes:
        source_name: Always 'gmail'
        config: Gmail-specific configuration from config.yaml
        redis_client: Redis client for cursor storage
        _gmail_service: Gmail API service instance (lazy initialized)
        _credentials: OAuth 2.0 credentials
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize Gmail reader with OAuth 2.0 credentials.

        Args:
            source_name: Source name (should be 'gmail')
            config: Gmail-specific configuration from config.yaml
            redis_client: Redis client for state management

        Raises:
            ValueError: If required OAuth credentials are missing or invalid
        """
        super().__init__(source_name, config, redis_client)

        # Validate OAuth 2.0 credentials
        self.validate_credentials([
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_OAUTH_REFRESH_TOKEN",
        ])

        # Gmail API service (lazy initialization)
        self._gmail_service: Any = None
        self._credentials: Any = None

        self.logger.info(
            f"Gmail reader initialized for source '{source_name}'",
            extra={"source": source_name},
        )

    def get_api_client(self) -> Any:
        """Lazy initialization of Gmail API service.

        Returns:
            Gmail API service instance configured with OAuth credentials

        Note:
            This method initializes the reader using OAuth refresh token from
            environment variables (GOOGLE_OAUTH_REFRESH_TOKEN).
        """
        if self._gmail_service is None:
            self.logger.debug("Initializing LlamaIndex GmailReader with OAuth credentials")

            try:
                from google.auth.transport.requests import Request  # type: ignore[import-not-found]
                from google.oauth2.credentials import Credentials  # type: ignore[import-not-found]

                # Gmail API scopes
                scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

                # Create credentials from refresh token
                creds = Credentials(
                    token=None,  # Will be refreshed
                    refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.environ["GOOGLE_CLIENT_ID"],
                    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                    scopes=scopes,
                )

                # Refresh the access token
                creds.refresh(Request())

                self.logger.debug("OAuth credentials refreshed successfully")

                # Build Gmail API service
                from googleapiclient.discovery import build  # type: ignore[import-not-found]

                self._gmail_service = build("gmail", "v1", credentials=creds)
                self._credentials = creds

                self.logger.info(
                    "Gmail API service initialized successfully with OAuth credentials"
                )

            except ImportError as e:
                self.logger.error(
                    "Required Google auth libraries not installed",
                    extra={"source": self.source_name, "error": str(e)},
                )
                raise ImportError(
                    "Missing required libraries. Install with: "
                    "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
                ) from e
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize Gmail API client: {e}",
                    extra={"source": self.source_name, "error": str(e)},
                )
                raise

        return self._gmail_service

    def supports_incremental_sync(self) -> bool:
        """Check if incremental sync is supported.

        Returns:
            True - Gmail supports incremental sync via date-based queries

        Note:
            Although LlamaIndex GmailReader does NOT support historyId,
            we implement incremental sync using Gmail search operators with
            date filtering (e.g., after:2024/09/30).
        """
        return True

    def load_data(
        self,
        progress_callback: Any = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Load emails from Gmail with optional incremental sync.

        This method:
        1. Retrieves last sync date from cursor (if exists)
        2. Builds Gmail query with search operators
        3. Fetches messages using Gmail API v1 directly
        4. Parses email content (subject, body, sender, recipients, timestamp)
        5. Includes attachment metadata if configured
        6. Converts to Document model
        7. Updates cursor to current date

        Args:
            **kwargs: Optional override parameters
                labels: List of labels to filter (default from config)
                query: Custom Gmail query (overrides auto-generated query)
                max_results: Maximum emails to fetch (default 500)
                ignore_cursor: Skip cursor for full re-ingestion (default False)

        Returns:
            List of Document objects representing emails

        Raises:
            Exception: Various Gmail API errors (auth, network, quota)

        Example:
            >>> reader = GmailReader('gmail', config, redis_client)
            >>> # First sync - fetches all emails from configured labels
            >>> documents = reader.load_data()
            >>> # Subsequent syncs - only new emails since last sync
            >>> documents = reader.load_data()
        """
        # Get configuration
        labels = kwargs.get("labels", self.config.get("labels", ["INBOX"]))
        max_results = kwargs.get("max_results", self.config.get("max_results", 500))
        include_attachments = self.config.get("include_attachments_metadata", True)
        ignore_cursor = kwargs.get("ignore_cursor", False)

        # Build query with incremental sync support
        query = kwargs.get("query")
        if not query:
            query = self._build_query(labels, ignore_cursor=ignore_cursor)

        self.logger.info(
            f"Loading Gmail messages with query: {query}",
            extra={
                "source": self.source_name,
                "labels": labels,
                "query": query,
                "max_results": max_results,
            },
        )

        try:
            # Get Gmail API service
            service = self.get_api_client()

            # Search for messages matching query
            messages_response = service.users().messages().list(
                userId="me", q=query, maxResults=min(max_results, 500)
            ).execute()

            message_ids = messages_response.get("messages", [])

            self.logger.debug(
                f"Found {len(message_ids)} messages matching query",
                extra={"source": self.source_name, "count": len(message_ids)},
            )

            # Fetch full message details
            documents = []
            error_count = 0
            max_email_timestamp = None  # Track latest email timestamp for cursor

            for msg_id_obj in message_ids:
                try:
                    msg_id = msg_id_obj["id"]

                    # Get full message
                    full_message = service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ).execute()

                    # Convert to Document
                    doc = self._convert_to_document(full_message, include_attachments)
                    documents.append(doc)

                    # Track max timestamp from email metadata
                    email_timestamp = doc.metadata.timestamp
                    if max_email_timestamp is None or email_timestamp > max_email_timestamp:
                        max_email_timestamp = email_timestamp

                except Exception as e:
                    error_count += 1
                    self.logger.warning(
                        f"Failed to process Gmail message: {e}",
                        extra={
                            "source": self.source_name,
                            "message_id": msg_id_obj.get("id", "unknown"),
                            "error": str(e),
                        },
                    )
                    continue

            self.logger.info(
                f"Fetched {len(documents)} messages from Gmail",
                extra={
                    "source": self.source_name,
                    "fetched_count": len(documents),
                    "error_count": error_count,
                },
            )

            # Update cursor to max email timestamp (only if emails were fetched)
            if documents and max_email_timestamp:
                cursor_date = max_email_timestamp.strftime("%Y/%m/%d")
                self.set_last_cursor(cursor_date)
                self.logger.info(
                    f"Updated cursor to max email date: {cursor_date}",
                    extra={"source": self.source_name, "cursor": cursor_date},
                )

            self.log_load_summary(
                total_fetched=len(message_ids),
                filtered_count=0,
                error_count=error_count,
                labels=labels,
                query=query,
            )

            return documents

        except Exception as e:
            self.logger.error(
                f"Failed to load Gmail messages: {e}",
                extra={
                    "source": self.source_name,
                    "error": str(e),
                    "query": query,
                },
                exc_info=True,
            )
            raise

    def _build_query(self, labels: list[str], ignore_cursor: bool = False) -> str:
        """Build Gmail search query with incremental sync support.

        Constructs query using Gmail search operators:
        - If cursor exists and not ignored: "after:YYYY/MM/DD label:INBOX label:SENT"
        - If no cursor or cursor ignored (full sync): "label:INBOX label:SENT"
        - Appends any configured query_filters (e.g., "from:user@example.com", "has:attachment")

        Args:
            labels: List of Gmail labels to filter (e.g., ["INBOX", "SENT"])
            ignore_cursor: Skip cursor for full re-ingestion (default False)

        Returns:
            Gmail search query string

        Example:
            >>> # First sync (no cursor)
            >>> query = reader._build_query(["INBOX", "SENT"])
            >>> print(query)  # "label:INBOX label:SENT"
            >>>
            >>> # Subsequent sync (has cursor: 2024/09/30)
            >>> query = reader._build_query(["INBOX"])
            >>> print(query)  # "after:2024/09/30 label:INBOX"
            >>>
            >>> # Full re-ingestion (ignore cursor)
            >>> query = reader._build_query(["INBOX"], ignore_cursor=True)
            >>> print(query)  # "label:INBOX"
            >>>
            >>> # With query filters
            >>> # config.yaml: query_filters: ["from:alice@example.com", "has:attachment"]
            >>> query = reader._build_query(["INBOX"])
            >>> print(query)  # "label:INBOX from:alice@example.com has:attachment"
        """
        query_parts = []

        # Add date filter if cursor exists and not ignored (incremental sync)
        cursor = self.get_last_cursor()
        if cursor and not ignore_cursor:
            # Cursor is stored in YYYY/MM/DD format (Gmail search operator format)
            query_parts.append(f"after:{cursor}")
            self.logger.debug(
                f"Using incremental sync with cursor: {cursor}",
                extra={"source": self.source_name, "cursor": cursor},
            )
        elif ignore_cursor and cursor:
            self.logger.info(
                f"Ignoring cursor for full re-ingestion (cursor was: {cursor})",
                extra={"source": self.source_name, "cursor": cursor},
            )

        # Add label filters with OR logic
        # Gmail requires uppercase OR operator between labels
        if labels:
            label_queries = [f"label:{label}" for label in labels]
            if len(label_queries) == 1:
                query_parts.append(label_queries[0])
            else:
                # Use OR operator for multiple labels (must be uppercase)
                label_query = " OR ".join(label_queries)
                query_parts.append(f"({label_query})")

        # Add configured query filters (e.g., "from:user@example.com", "has:attachment")
        query_filters = self.config.get("query_filters", [])
        if query_filters:
            query_parts.extend(query_filters)
            self.logger.debug(
                f"Applied query filters: {query_filters}",
                extra={"source": self.source_name, "filters": query_filters},
            )

        query = " ".join(query_parts)

        return query if query else "label:INBOX"  # Default to INBOX if empty

    def _decode_base64url(self, data: str) -> str:
        """Decode base64url-encoded string.

        Gmail uses URL-safe base64 encoding for message bodies.

        Args:
            data: Base64url-encoded string

        Returns:
            Decoded UTF-8 string
        """
        decoded_bytes = base64.urlsafe_b64decode(data)
        return decoded_bytes.decode("utf-8")

    def _parse_message_parts(
        self, parts: list[dict[str, Any]], mime_type: str = "text/plain"
    ) -> str | None:
        """Recursively parse message parts to find specific MIME type.

        Gmail messages can be multipart with nested structures.
        This method searches recursively for the desired MIME type.

        Args:
            parts: List of message parts from Gmail API
            mime_type: Target MIME type (default: text/plain)

        Returns:
            Decoded body content or None if not found
        """
        for part in parts:
            # Check if this part matches the desired MIME type
            if part.get("mimeType") == mime_type:
                if "data" in part.get("body", {}):
                    return self._decode_base64url(part["body"]["data"])

            # Recursively search nested parts
            if "parts" in part:
                result = self._parse_message_parts(part["parts"], mime_type)
                if result:
                    return result

        return None

    def _get_message_body(self, message: dict[str, Any]) -> str:
        """Extract message body from Gmail API message.

        Tries to get plain text body, falls back to HTML.

        Args:
            message: Full message object from Gmail API

        Returns:
            Message body text (empty string if not found)
        """
        if "payload" not in message:
            return ""

        payload = message["payload"]

        # Simple message (non-multipart)
        if "body" in payload and "data" in payload["body"]:
            return self._decode_base64url(payload["body"]["data"])

        # Multipart message - try plain text first, then HTML
        if "parts" in payload:
            text_body = self._parse_message_parts(payload["parts"], "text/plain")
            if text_body:
                return text_body

            html_body = self._parse_message_parts(payload["parts"], "text/html")
            if html_body:
                return html_body

        return ""

    def _get_headers(self, message: dict[str, Any]) -> dict[str, str]:
        """Extract headers from Gmail message.

        Args:
            message: Gmail API message object

        Returns:
            Dictionary of header name -> value
        """
        headers = {}

        if "payload" in message and "headers" in message["payload"]:
            for header in message["payload"]["headers"]:
                headers[header["name"]] = header["value"]

        return headers

    def _convert_to_document(
        self,
        gmail_message: dict[str, Any],
        include_attachments: bool = True,
    ) -> Document:
        """Convert Gmail API message to our Document model.

        Extracts email content and metadata from Gmail API response:
        - Subject (title)
        - Body (content - plain text or HTML)
        - Sender, recipients
        - Timestamp
        - Attachment metadata (if enabled)

        Args:
            gmail_message: Gmail API message object (full format)
            include_attachments: Whether to include attachment metadata

        Returns:
            Document object with email content and metadata

        Note:
            Email body is extracted from message payload (multipart supported).
            Attachments are metadata only - we don't download files.
        """
        # Get message ID
        message_id = gmail_message.get("id", "unknown")

        # Extract headers
        headers = self._get_headers(gmail_message)
        subject = headers.get("Subject", "(No Subject)")
        sender = headers.get("From", "unknown@unknown.com")
        recipients = headers.get("To", "")
        date_str = headers.get("Date", "")

        # Parse timestamp from Date header
        try:
            # Try parsing RFC 2822 format (standard email date format)
            from email.utils import parsedate_to_datetime

            timestamp = parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            # Fallback to current time if parsing fails
            timestamp = datetime.now()
            self.logger.warning(
                f"Failed to parse email timestamp: {date_str}, using current time",
                extra={"source": self.source_name, "message_id": message_id},
            )

        # Get email body
        content = self._get_message_body(gmail_message)

        # Build doc_id from message_id
        doc_id = f"gmail_{message_id}"

        # Compute content hash for deduplication
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Build extra metadata
        extra_metadata: dict[str, Any] = {
            "sender": sender,
            "recipients": recipients,
            "message_id": message_id,
            "snippet": gmail_message.get("snippet", ""),
        }

        # Add attachment metadata if enabled
        if include_attachments and "payload" in gmail_message:
            attachments = self._extract_attachments(gmail_message["payload"])
            if attachments:
                extra_metadata["attachments"] = attachments
                extra_metadata["attachment_count"] = len(attachments)

        # Create DocumentMetadata
        doc_metadata = DocumentMetadata(
            source_type="gmail",
            source_url=f"https://mail.google.com/mail/u/0/#inbox/{message_id}",
            timestamp=timestamp,
            extra=extra_metadata,
        )

        # Create Document
        document = Document(
            doc_id=doc_id,
            title=subject,
            content=content,
            content_hash=content_hash,
            metadata=doc_metadata,
            embedding=None,
        )

        return document

    def _extract_attachments(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract attachment metadata from message payload.

        Args:
            payload: Message payload from Gmail API

        Returns:
            List of attachment metadata dictionaries
        """
        attachments = []

        def extract_from_parts(parts: list[dict[str, Any]]) -> None:
            for part in parts:
                if part.get("filename"):
                    attachment = {
                        "filename": part["filename"],
                        "mimeType": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                    }
                    attachments.append(attachment)

                # Recursively check nested parts
                if "parts" in part:
                    extract_from_parts(part["parts"])

        if "parts" in payload:
            extract_from_parts(payload["parts"])

        return attachments


def get_refresh_token() -> str:
    """Helper function to obtain OAuth 2.0 refresh token for Gmail API.

    This function performs the initial OAuth consent flow to obtain a refresh token
    that can be stored in .env file for subsequent API calls.

    OAuth Setup Steps:
    1. Go to Google Cloud Console: https://console.cloud.google.com/
    2. Create a new project (or select existing)
    3. Navigate to "APIs & Services" -> "Library"
    4. Search for "Gmail API" and enable it
    5. Go to "APIs & Services" -> "Credentials"
    6. Configure OAuth Consent Screen:
       - Choose "Internal" (for Workspace) or "External"
       - Fill in application name, user support email, developer email
       - Add scope: https://www.googleapis.com/auth/gmail.readonly
    7. Create OAuth Client ID:
       - Click "Create Credentials" -> "OAuth client ID"
       - Application type: "Desktop app"
       - Download credentials JSON
    8. Run this function with CLIENT_ID and CLIENT_SECRET from downloaded file
    9. Follow the authentication flow in browser
    10. Copy the refresh token to GOOGLE_OAUTH_REFRESH_TOKEN in .env

    Returns:
        OAuth 2.0 refresh token string

    Example:
        >>> from llamacrawl.readers.gmail import get_refresh_token
        >>> # Set environment variables first:
        >>> # export GOOGLE_CLIENT_ID="xxx.apps.googleusercontent.com"
        >>> # export GOOGLE_CLIENT_SECRET="xxx"
        >>> refresh_token = get_refresh_token()
        >>> # Follow browser prompts to authorize
        >>> print(f"Refresh token: {refresh_token}")
        >>> # Add to .env: GOOGLE_OAUTH_REFRESH_TOKEN={refresh_token}

    Raises:
        ValueError: If GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set
        Exception: If OAuth flow fails
    """
    # Check required credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set. "
            "Get them from Google Cloud Console OAuth credentials."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-not-found]

        # Gmail API scopes
        scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

        # Create credentials dict for OAuth flow
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

        # Run OAuth flow
        flow = InstalledAppFlow.from_client_config(client_config, scopes)
        creds = flow.run_local_server(port=0)

        # Return refresh token
        if creds and creds.refresh_token:
            print("\n✓ OAuth authentication successful!")
            print(f"\nRefresh Token: {creds.refresh_token}")
            print("\nAdd this to your .env file:")
            print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
            return str(creds.refresh_token)
        else:
            raise Exception("Failed to obtain refresh token from OAuth flow")

    except ImportError as e:
        raise ImportError(
            "Required libraries not installed. Run: "
            "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        ) from e
    except Exception as e:
        raise Exception(f"OAuth flow failed: {e}") from e
