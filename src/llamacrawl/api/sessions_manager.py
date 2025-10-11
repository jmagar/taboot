"""Sessions watcher manager orchestrating file monitoring and ingestion.

This module provides SessionsWatcherManager for real-time monitoring of AI coding assistant
session files (Claude Code, Codex CLI) and automatic ingestion into LlamaCrawl's RAG pipeline.

Architecture:
    - Follows FirecrawlJobManager pattern with shared heavy clients
    - Starts background task for processing file change events
    - Uses SessionsWatcher for file system monitoring
    - Processes both message-level and conversation-level documents
    - Graceful shutdown with task cancellation

Lifecycle:
    - Initialize with shared clients (no client creation in __init__)
    - start(): Validate paths, initialize watcher, spawn background task
    - shutdown(): Stop watcher, cancel tasks, wait for completion

File Change Processing:
    1. SessionsWatcher detects .jsonl file modification
    2. Event queued via asyncio.Queue
    3. Background task processes event
    4. Determine reader type (claude/codex) from path
    5. Load new documents from file (after cursor)
    6. Check conversation stability for conversation-level docs
    7. Ingest through IngestionPipeline
    8. Update cursors in Redis

Error Handling:
    - Per-file error handling prevents one bad file from crashing watcher
    - Per-document error handling via IngestionPipeline DLQ
    - Graceful cancellation via asyncio.CancelledError
    - Logs errors but continues processing
"""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

from llamacrawl.config import Config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.ingestion.pipeline import IngestionPipeline
from llamacrawl.readers.sessions.claude import ClaudeCodeReader
from llamacrawl.readers.sessions.codex import CodexReader
from llamacrawl.readers.sessions.watcher import SessionsWatcher
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class SessionsWatcherManager:
    """Manages file watching and ingestion for AI coding assistant sessions.

    This class coordinates real-time monitoring of session directories and
    automatic ingestion of new conversation data into the RAG pipeline.

    Follows the FirecrawlJobManager pattern:
    - Takes shared heavy clients in __init__ (no initialization)
    - Starts background processing task via start()
    - Provides graceful shutdown()

    Attributes:
        _config: Configuration object with sessions source settings
        _redis_client: Redis client for cursor tracking and stability
        _qdrant_client: Qdrant client for vector storage
        _neo4j_client: Neo4j client for graph storage
        _embed_model: TEI embedding model for generating embeddings
        _watcher_task: Background asyncio task processing file events
        _watcher: SessionsWatcher instance for file monitoring
        _event_queue: Queue for file change events from watcher
    """

    def __init__(
        self,
        config: Config,
        redis_client: RedisClient,
        qdrant_client: QdrantClient,
        neo4j_client: Neo4jClient,
        embed_model: TEIEmbedding,
    ) -> None:
        """Initialize sessions watcher manager with shared clients.

        Args:
            config: Configuration object with sessions source settings
            redis_client: Shared Redis client for state management
            qdrant_client: Shared Qdrant client for vector storage
            neo4j_client: Shared Neo4j client for graph storage
            embed_model: Shared TEI embedding model

        Note:
            Does NOT initialize heavy clients - reuses ones passed in.
            This allows sharing clients between multiple managers.
        """
        self._config = config
        self._redis_client = redis_client
        self._qdrant_client = qdrant_client
        self._neo4j_client = neo4j_client
        self._embed_model = embed_model

        self._watcher_task: asyncio.Task[None] | None = None
        self._watcher: SessionsWatcher | None = None
        self._event_queue: asyncio.Queue[Path] = asyncio.Queue()

    async def start(self) -> None:
        """Start file watching and background ingestion task.

        Validates configured paths exist, initializes SessionsWatcher,
        starts the Observer, and spawns background event processing task.

        Raises:
            ValueError: If no watch paths are configured or paths don't exist
            RuntimeError: If already started

        Example:
            >>> manager = SessionsWatcherManager(config, redis, qdrant, neo4j, embed)
            >>> await manager.start()
            >>> # ... sessions are now monitored ...
            >>> await manager.shutdown()
        """
        if self._watcher_task is not None:
            raise RuntimeError("SessionsWatcherManager already started")

        sessions_config = self._config.sources.sessions

        # Validate at least one watch path is configured
        watch_paths: list[Path] = []

        if sessions_config.claude_code_path:
            claude_path = sessions_config.claude_code_path.expanduser()
            if not claude_path.exists():
                raise ValueError(
                    f"Claude Code path does not exist: {claude_path}"
                )
            if not claude_path.is_dir():
                raise ValueError(
                    f"Claude Code path is not a directory: {claude_path}"
                )
            watch_paths.append(claude_path)
            logger.info(
                f"Watching Claude Code sessions at {claude_path}",
                extra={"watch_path": str(claude_path)},
            )

        if sessions_config.codex_path:
            codex_path = sessions_config.codex_path.expanduser()
            if not codex_path.exists():
                raise ValueError(f"Codex path does not exist: {codex_path}")
            if not codex_path.is_dir():
                raise ValueError(f"Codex path is not a directory: {codex_path}")
            watch_paths.append(codex_path)
            logger.info(
                f"Watching Codex CLI sessions at {codex_path}",
                extra={"watch_path": str(codex_path)},
            )

        if not watch_paths:
            raise ValueError(
                "No valid watch paths configured for sessions ingestion"
            )

        # Initialize SessionsWatcher with callback that queues events
        def on_file_modified(file_path: Path) -> None:
            """Callback invoked by SessionsWatcher on file modifications.

            Queues the file path for async processing by background task.
            Runs in watchdog Observer thread, so uses thread-safe Queue.put_nowait.
            """
            try:
                # Queue.put_nowait is thread-safe
                self._event_queue.put_nowait(file_path)
            except asyncio.QueueFull:
                logger.warning(
                    f"Event queue full, dropping file change event for {file_path}",
                    extra={"file_path": str(file_path)},
                )

        self._watcher = SessionsWatcher(
            watch_paths=watch_paths, event_callback=on_file_modified
        )

        # Start the file watcher (Observer thread)
        self._watcher.start()

        logger.info(
            f"SessionsWatcher started monitoring {len(watch_paths)} path(s)",
            extra={"watch_path_count": len(watch_paths)},
        )

        # Start background task for processing events
        self._watcher_task = asyncio.create_task(self._process_events_loop())

        logger.info("SessionsWatcherManager background task started")

    async def shutdown(self) -> None:
        """Stop file watching and cancel background tasks.

        Gracefully shuts down:
        1. Stop SessionsWatcher Observer
        2. Cancel background event processing task
        3. Wait for task completion with suppressed CancelledError

        Safe to call multiple times (idempotent).

        Example:
            >>> await manager.shutdown()
        """
        logger.info("Shutting down SessionsWatcherManager")

        # Stop the file watcher
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
            logger.info("SessionsWatcher stopped")

        # Cancel background task
        if self._watcher_task is not None:
            self._watcher_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._watcher_task
            self._watcher_task = None
            logger.info("Background event processing task cancelled")

        logger.info("SessionsWatcherManager shutdown complete")

    async def _process_events_loop(self) -> None:
        """Background coroutine that processes file change events.

        Runs infinite loop pulling events from queue and processing them.
        Handles cancellation gracefully via CancelledError.

        Per-file error handling prevents one bad file from crashing the loop.
        """
        logger.info("Starting file change event processing loop")

        try:
            while True:
                # Wait for file change event (blocking)
                file_path = await self._event_queue.get()

                logger.debug(
                    f"Processing file change event for {file_path.name}",
                    extra={"file_path": str(file_path)},
                )

                # Process the file change with error handling
                try:
                    await self._handle_file_change(file_path)
                except Exception as e:
                    logger.error(
                        f"Failed to process file change for {file_path}: {e}",
                        extra={
                            "file_path": str(file_path),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    # Continue processing other events
                    continue

        except asyncio.CancelledError:
            logger.info("Event processing loop cancelled, shutting down gracefully")
            raise

    async def _handle_file_change(self, file_path: Path) -> None:
        """Handle a file modification event.

        Determines reader type from path, loads new documents, checks conversation
        stability, and ingests through pipeline.

        Args:
            file_path: Path to modified JSONL file

        Raises:
            ValueError: If file path doesn't match any known session source
            Exception: Various exceptions from reader or pipeline (logged and raised)
        """
        sessions_config = self._config.sources.sessions

        # Determine source type from file path
        source_type: str
        reader_class: type[ClaudeCodeReader] | type[CodexReader]

        if (
            sessions_config.claude_code_path
            and file_path.is_relative_to(
                sessions_config.claude_code_path.expanduser()
            )
        ):
            source_type = "claude_code"
            reader_class = ClaudeCodeReader
        elif (
            sessions_config.codex_path
            and file_path.is_relative_to(sessions_config.codex_path.expanduser())
        ):
            source_type = "codex"
            reader_class = CodexReader
        else:
            raise ValueError(
                f"File path {file_path} does not match any configured session source"
            )

        logger.info(
            f"Processing {source_type} session file: {file_path.name}",
            extra={"source_type": source_type, "file_path": str(file_path)},
        )

        # Process message-level documents if enabled
        if sessions_config.enable_message_level:
            await self._process_message_level_docs(
                file_path, source_type, reader_class
            )

        # Process conversation-level document if enabled and stable
        if sessions_config.enable_conversation_level:
            if self._check_conversation_stability(file_path):
                await self._process_conversation_level_doc(
                    file_path, source_type, reader_class
                )
            else:
                logger.debug(
                    f"Conversation not yet stable for {file_path.name}, skipping conversation-level doc",
                    extra={
                        "source_type": source_type,
                        "file_path": str(file_path),
                    },
                )

    async def _process_message_level_docs(
        self,
        file_path: Path,
        source_type: str,
        reader_class: type[ClaudeCodeReader] | type[CodexReader],
    ) -> None:
        """Load and ingest message-level documents from file.

        Uses blocking I/O in thread to load documents, then ingests through pipeline.

        Args:
            file_path: Path to JSONL file
            source_type: Source type ('claude_code' or 'codex')
            reader_class: Reader class to instantiate
        """
        # Initialize reader (runs in thread for blocking I/O)
        def load_documents() -> list[Any]:
            """Load documents in thread to avoid blocking event loop."""
            # ClaudeCodeReader uses SessionReader.__init__(source_name, config, redis_client)
            # CodexReader overrides __init__(config, redis_client) and passes "codex" internally
            reader: ClaudeCodeReader | CodexReader
            if source_type == "codex":
                reader = CodexReader(
                    config=self._config.sources.sessions.model_dump(),
                    redis_client=self._redis_client,
                )
            else:  # claude_code
                reader = ClaudeCodeReader(
                    source_name=source_type,
                    config=self._config.sources.sessions.model_dump(),
                    redis_client=self._redis_client,
                )
            return reader.load_data(file_paths=[file_path])

        # Load documents in thread
        documents = await asyncio.to_thread(load_documents)

        if not documents:
            logger.debug(
                f"No new message-level documents in {file_path.name}",
                extra={"source_type": source_type, "file_path": str(file_path)},
            )
            return

        logger.info(
            f"Loaded {len(documents)} message-level document(s) from {file_path.name}",
            extra={
                "source_type": source_type,
                "file_path": str(file_path),
                "document_count": len(documents),
            },
        )

        # Ingest through pipeline (blocking operation)
        def ingest_documents() -> dict[str, Any]:
            """Run ingestion in thread to avoid blocking event loop."""
            pipeline = IngestionPipeline(
                config=self._config,
                redis_client=self._redis_client,
                qdrant_client=self._qdrant_client,
                neo4j_client=self._neo4j_client,
                embed_model=self._embed_model,
            )
            summary = pipeline.ingest_documents(
                source=f"sessions_{source_type}", documents=documents
            )
            return summary.to_dict()

        summary = await asyncio.to_thread(ingest_documents)

        logger.info(
            f"Ingested message-level documents from {file_path.name}",
            extra={
                "source_type": source_type,
                "file_path": str(file_path),
                **summary,
            },
        )

    async def _process_conversation_level_doc(
        self,
        file_path: Path,
        source_type: str,
        reader_class: type[ClaudeCodeReader] | type[CodexReader],
    ) -> None:
        """Generate and ingest conversation-level document for stable conversation.

        Reads entire file, generates markdown transcript, and ingests.

        Args:
            file_path: Path to JSONL file
            source_type: Source type ('claude_code' or 'codex')
            reader_class: Reader class to instantiate
        """
        logger.info(
            f"Generating conversation-level document for {file_path.name}",
            extra={"source_type": source_type, "file_path": str(file_path)},
        )

        # Generate conversation document (runs in thread)
        def generate_conversation_doc() -> Any | None:
            """Generate conversation document in thread."""
            # Create temporary reader without cursor to read full file
            # ClaudeCodeReader uses SessionReader.__init__(source_name, config, redis_client)
            # CodexReader overrides __init__(config, redis_client) and passes "codex" internally
            reader: ClaudeCodeReader | CodexReader
            if source_type == "codex":
                reader = CodexReader(
                    config=self._config.sources.sessions.model_dump(),
                    redis_client=self._redis_client,
                )
            else:  # claude_code
                reader = ClaudeCodeReader(
                    source_name=source_type,
                    config=self._config.sources.sessions.model_dump(),
                    redis_client=self._redis_client,
                )

            # Read all lines from file (ignoring cursor)
            # We'll temporarily reset cursor to -1 to read from start
            file_hash = reader._hash_file_path(file_path)
            cursor_key = f"sessions:cursor:{source_type}:{file_hash}"
            original_cursor = self._redis_client.client.get(cursor_key)

            try:
                # Temporarily reset cursor to read full file
                self._redis_client.client.set(cursor_key, "-1")

                # Load all messages
                all_documents = reader.load_data(file_paths=[file_path])

                if not all_documents:
                    return None

                # Restore original cursor
                if original_cursor is not None:
                    self._redis_client.client.set(cursor_key, original_cursor)
                else:
                    self._redis_client.client.delete(cursor_key)

                # Build markdown transcript
                return self._build_conversation_document(
                    all_documents, file_path, source_type
                )

            except Exception:
                # Restore cursor on error
                if original_cursor is not None:
                    self._redis_client.client.set(cursor_key, original_cursor)
                raise

        conversation_doc = await asyncio.to_thread(generate_conversation_doc)

        if conversation_doc is None:
            logger.warning(
                f"Failed to generate conversation document for {file_path.name}",
                extra={"source_type": source_type, "file_path": str(file_path)},
            )
            return

        # Ingest conversation document
        def ingest_conversation() -> dict[str, Any]:
            """Ingest conversation document in thread."""
            pipeline = IngestionPipeline(
                config=self._config,
                redis_client=self._redis_client,
                qdrant_client=self._qdrant_client,
                neo4j_client=self._neo4j_client,
                embed_model=self._embed_model,
            )
            summary = pipeline.ingest_documents(
                source=f"sessions_{source_type}_conversation",
                documents=[conversation_doc],
            )
            return summary.to_dict()

        summary = await asyncio.to_thread(ingest_conversation)

        logger.info(
            f"Ingested conversation-level document for {file_path.name}",
            extra={
                "source_type": source_type,
                "file_path": str(file_path),
                **summary,
            },
        )

    def _check_conversation_stability(self, file_path: Path) -> bool:
        """Check if conversation has been stable for configured time period.

        Uses Redis to track last modification timestamp and compares to current file mtime.

        Args:
            file_path: Path to JSONL file

        Returns:
            True if file hasn't changed for conversation_stable_time seconds

        Example:
            >>> manager._check_conversation_stability(Path("session.jsonl"))
            False  # File recently modified
            >>> # Wait 10 minutes...
            >>> manager._check_conversation_stability(Path("session.jsonl"))
            True  # File stable
        """
        current_mtime = file_path.stat().st_mtime
        stable_time = self._config.sources.sessions.conversation_stable_time

        # Generate Redis key for stability tracking
        import hashlib

        path_str = str(file_path.resolve())
        file_hash = hashlib.sha256(path_str.encode("utf-8")).hexdigest()[:16]
        stability_key = f"sessions:stable:{file_hash}"

        # Get last known mtime from Redis
        last_mtime_str = self._redis_client.client.get(stability_key)

        if last_mtime_str is None:
            # First time seeing this file, store mtime
            self._redis_client.client.set(stability_key, str(current_mtime))
            logger.debug(
                f"Tracking new file for stability: {file_path.name}",
                extra={
                    "file_path": str(file_path),
                    "mtime": current_mtime,
                    "stability_key": stability_key,
                },
            )
            return False

        try:
            last_mtime = float(last_mtime_str)
        except (ValueError, TypeError):
            # Invalid stored value, reset
            self._redis_client.client.set(stability_key, str(current_mtime))
            return False

        # Check if file has changed
        if current_mtime > last_mtime:
            # File modified, update timestamp
            self._redis_client.client.set(stability_key, str(current_mtime))
            logger.debug(
                f"File modification detected, resetting stability timer for {file_path.name}",
                extra={
                    "file_path": str(file_path),
                    "last_mtime": last_mtime,
                    "current_mtime": current_mtime,
                },
            )
            return False

        # File hasn't changed, check if enough time has passed
        elapsed = time.time() - current_mtime
        is_stable = elapsed >= stable_time

        if is_stable:
            logger.info(
                f"Conversation stable for {file_path.name} (elapsed: {elapsed:.0f}s)",
                extra={
                    "file_path": str(file_path),
                    "elapsed_seconds": elapsed,
                    "stable_time": stable_time,
                },
            )
        else:
            logger.debug(
                f"Conversation not yet stable for {file_path.name} (elapsed: {elapsed:.0f}s, required: {stable_time}s)",
                extra={
                    "file_path": str(file_path),
                    "elapsed_seconds": elapsed,
                    "stable_time": stable_time,
                },
            )

        return is_stable

    def _build_conversation_document(
        self,
        all_documents: list[Any],
        file_path: Path,
        source_type: str,
    ) -> Any:
        """Build conversation-level document from all message documents.

        Creates markdown transcript with conversation metadata.

        Args:
            all_documents: List of message-level Document objects
            file_path: Path to JSONL file
            source_type: Source type ('claude_code' or 'codex')

        Returns:
            Document object with conversation-level content
        """
        from llamacrawl.models.document import Document, DocumentMetadata
        import hashlib

        if not all_documents:
            raise ValueError("Cannot build conversation document from empty list")

        # Extract session_id from first document
        first_doc = all_documents[0]
        session_id = first_doc.metadata.extra.get("session_id", "unknown")

        # Extract metadata for title generation
        working_directory = first_doc.metadata.extra.get(
            "working_directory", "unknown"
        )
        git_branch = first_doc.metadata.extra.get("git_branch")

        # Build markdown transcript
        transcript_parts: list[str] = []

        # Header
        first_user_message = next(
            (
                doc
                for doc in all_documents
                if doc.metadata.extra.get("message_role") == "user"
            ),
            None,
        )
        title = (
            first_user_message.content[:100] + "..."
            if first_user_message and len(first_user_message.content) > 100
            else first_user_message.content if first_user_message else "Conversation"
        )

        transcript_parts.append(f"# Conversation: {title}")
        transcript_parts.append(f"Project: {working_directory}")
        if git_branch:
            transcript_parts.append(f"Branch: {git_branch}")
        transcript_parts.append("")

        # Messages
        for doc in all_documents:
            role = doc.metadata.extra.get("message_role", "unknown")
            timestamp = doc.metadata.timestamp.strftime("%Y-%m-%d %H:%M")
            tools_used = doc.metadata.extra.get("tools_used", [])

            transcript_parts.append(f"## {role.title()} - {timestamp}")
            transcript_parts.append(doc.content)

            if tools_used:
                transcript_parts.append(f"Tools: {', '.join(tools_used)}")

            transcript_parts.append("")

        content = "\n".join(transcript_parts)

        # Generate content hash
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Create conversation-level document
        doc_id = f"conv:{session_id}"

        metadata = DocumentMetadata(
            source_type=source_type,
            source_url=f"file://{file_path.resolve()}",
            timestamp=first_doc.metadata.timestamp,
            extra={
                "session_id": session_id,
                "working_directory": working_directory,
                "git_branch": git_branch,
                "message_count": len(all_documents),
                "source_file": str(
                    file_path.relative_to(Path.home())
                    if file_path.is_relative_to(Path.home())
                    else file_path
                ),
            },
        )

        return Document(
            doc_id=doc_id,
            title=f"Conversation: {title}",
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )
