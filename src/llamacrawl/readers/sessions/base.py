"""Abstract base class for session file readers.

This module provides the SessionReader abstract base class that all session format readers
(Claude Code, Codex CLI, etc.) must inherit from. It extends BaseReader with session-specific
functionality including:

- JSONL line-by-line streaming with cursor management
- Per-file cursor tracking in Redis (sessions:cursor:{source_type}:{file_path_hash})
- Abstract _parse_line() method for format-specific parsing
- Graceful handling of malformed JSON lines
- Incremental sync support

Classes:
    SessionReader: Abstract base class for session readers

Usage:
    class MySessionReader(SessionReader):
        def _parse_line(
            self,
            line_data: dict[str, Any],
            file_path: Path,
            line_number: int
        ) -> Document | None:
            # Format-specific parsing logic
            return Document(...)
"""

import hashlib
import json
from abc import abstractmethod
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from llamacrawl.models.document import Document
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient


class SessionReader(BaseReader):
    """Abstract base class for session file readers.

    This class extends BaseReader to provide JSONL file streaming and per-file
    cursor management for AI coding assistant session logs. Subclasses implement
    format-specific parsing via _parse_line().

    Attributes:
        source_name: Name of the data source (e.g., 'claude_code', 'codex')
        config: Source-specific configuration
        redis_client: Redis client for cursor management
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize the session reader.

        Args:
            source_name: Name of the data source (e.g., 'claude_code', 'codex')
            config: Source-specific configuration from config.yaml
            redis_client: Redis client instance for state management

        Raises:
            ValueError: If source_name is empty or invalid
        """
        super().__init__(source_name, config, redis_client)

    def supports_incremental_sync(self) -> bool:
        """Check if this reader supports incremental synchronization.

        Session readers support incremental sync via per-file line number cursors.

        Returns:
            True - Session readers always support incremental sync
        """
        return True

    @abstractmethod
    def _parse_line(
        self,
        line_data: dict[str, Any],
        file_path: Path,
        line_number: int,
    ) -> Document | None:
        """Parse a single JSONL line into a Document.

        This method must be implemented by subclasses to handle format-specific
        parsing logic (Claude Code vs Codex CLI vs Gemini, etc.).

        Args:
            line_data: Parsed JSON object from JSONL line
            file_path: Path to the JSONL file being processed
            line_number: 0-indexed line number in the file

        Returns:
            Document object if line should be ingested, None to skip

        Raises:
            Exception: Format-specific parsing errors (caught by caller)

        Example:
            >>> def _parse_line(self, line_data, file_path, line_number):
            ...     if line_data.get("type") != "message":
            ...         return None  # Skip non-message entries
            ...     return Document(
            ...         doc_id=f"msg:{line_data['sessionId']}:{line_number}",
            ...         title=f"{line_data['userType']} message",
            ...         content=line_data['message'],
            ...         content_hash=hashlib.sha256(line_data['message'].encode()).hexdigest(),
            ...         metadata=DocumentMetadata(...)
            ...     )
        """
        pass

    def load_data(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
        file_paths: list[Path] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Load documents from JSONL session files.

        Streams lines from each file after the last processed cursor position,
        parses via _parse_line(), and updates cursors after successful processing.

        Args:
            progress_callback: Optional callback(current, total) for progress updates
            file_paths: List of JSONL file paths to process
            **kwargs: Additional parameters (unused, for BaseReader compatibility)

        Returns:
            List of Document objects from all processed files

        Raises:
            ValueError: If file_paths is empty or None
            FileNotFoundError: If any file does not exist
            PermissionError: If file is not readable

        Example:
            >>> reader = ClaudeCodeReader(...)
            >>> paths = [Path("~/.claude/projects/session1.jsonl")]
            >>> documents = reader.load_data(file_paths=paths)
        """
        if not file_paths:
            raise ValueError("file_paths parameter is required and cannot be empty")

        self.logger.info(
            f"Loading session data from {len(file_paths)} file(s)",
            extra={
                "source": self.source_name,
                "file_count": len(file_paths),
            },
        )

        all_documents: list[Document] = []
        total_lines_processed = 0
        error_count = 0

        for file_path in file_paths:
            # Validate file exists and is readable
            if not file_path.exists():
                raise FileNotFoundError(f"Session file not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")

            try:
                # Get last processed line number for this file
                last_line = self._get_file_cursor(file_path)

                self.logger.debug(
                    f"Processing file from line {last_line + 1}",
                    extra={
                        "source": self.source_name,
                        "file_path": str(file_path),
                        "last_line": last_line,
                    },
                )

                # Stream new lines from file
                documents_from_file: list[Document] = []
                latest_line_number = last_line

                for line_number, line_data in self._stream_jsonl_lines(file_path, last_line):
                    try:
                        # Parse line using format-specific logic
                        document = self._parse_line(line_data, file_path, line_number)

                        if document is not None:
                            documents_from_file.append(document)

                        latest_line_number = line_number

                    except Exception as e:
                        error_count += 1
                        self.logger.warning(
                            f"Failed to parse line {line_number} in {file_path}: {e}",
                            extra={
                                "source": self.source_name,
                                "file_path": str(file_path),
                                "line_number": line_number,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        # Continue processing remaining lines
                        continue

                # Update cursor after successful batch processing
                if latest_line_number > last_line:
                    self._set_file_cursor(file_path, latest_line_number)
                    total_lines_processed += latest_line_number - last_line

                all_documents.extend(documents_from_file)

                self.logger.info(
                    f"Processed {len(documents_from_file)} documents from {file_path.name}",
                    extra={
                        "source": self.source_name,
                        "file_path": str(file_path),
                        "document_count": len(documents_from_file),
                        "lines_processed": latest_line_number - last_line,
                    },
                )

            except Exception as e:
                error_count += 1
                self.logger.error(
                    f"Failed to process file {file_path}: {e}",
                    extra={
                        "source": self.source_name,
                        "file_path": str(file_path),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                # Continue processing remaining files
                continue

        # Log summary
        self.log_load_summary(
            total_fetched=len(all_documents),
            filtered_count=0,
            error_count=error_count,
            file_count=len(file_paths),
            lines_processed=total_lines_processed,
        )

        return all_documents

    def _stream_jsonl_lines(
        self,
        file_path: Path,
        last_line: int,
    ) -> Iterator[tuple[int, dict[str, Any]]]:
        """Stream JSONL lines from file after cursor position.

        Safely handles concurrent read/write, empty lines, and malformed JSON.
        Lines are 0-indexed.

        Args:
            file_path: Path to JSONL file
            last_line: Last processed line number (0-indexed)

        Yields:
            Tuple of (line_number, parsed_json_object) for valid lines

        Example:
            >>> for line_num, data in reader._stream_jsonl_lines(path, 42):
            ...     print(f"Line {line_num}: {data['type']}")
        """
        with open(file_path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=0):
                # Skip already processed lines
                if line_number <= last_line:
                    continue

                # Skip empty lines
                line = line.strip()
                if not line:
                    self.logger.debug(
                        f"Skipping empty line {line_number} in {file_path.name}",
                        extra={
                            "source": self.source_name,
                            "file_path": str(file_path),
                            "line_number": line_number,
                        },
                    )
                    continue

                # Parse JSON with error handling
                try:
                    line_data = json.loads(line)
                    yield (line_number, line_data)

                except json.JSONDecodeError as e:
                    # Malformed JSON - likely partial write, skip for now
                    # Will be picked up on next file change event
                    self.logger.debug(
                        f"Skipping malformed JSON at line {line_number} in {file_path.name}: {e}",
                        extra={
                            "source": self.source_name,
                            "file_path": str(file_path),
                            "line_number": line_number,
                            "error": str(e),
                        },
                    )
                    continue

    def _get_file_cursor(self, file_path: Path) -> int:
        """Get last processed line number for a file.

        Args:
            file_path: Path to JSONL file

        Returns:
            Last processed line number (0-indexed), or -1 if no previous processing
        """
        file_hash = self._hash_file_path(file_path)
        cursor_key = f"sessions:cursor:{self.source_name}:{file_hash}"

        cursor_value = self.redis_client.client.get(cursor_key)

        if cursor_value is None:
            self.logger.debug(
                f"No cursor found for file {file_path.name} (first processing)",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "cursor_key": cursor_key,
                },
            )
            return -1

        try:
            line_number = int(cursor_value)
            self.logger.debug(
                f"Retrieved cursor for file {file_path.name}: line {line_number}",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "line_number": line_number,
                    "cursor_key": cursor_key,
                },
            )
            return line_number

        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Invalid cursor value for {file_path.name}: {cursor_value}, resetting to -1",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "cursor_value": cursor_value,
                    "error": str(e),
                },
            )
            return -1

    def _set_file_cursor(self, file_path: Path, line_number: int) -> None:
        """Update last processed line number for a file.

        Args:
            file_path: Path to JSONL file
            line_number: Line number to store (0-indexed)
        """
        file_hash = self._hash_file_path(file_path)
        cursor_key = f"sessions:cursor:{self.source_name}:{file_hash}"

        self.redis_client.client.set(cursor_key, str(line_number))

        self.logger.debug(
            f"Updated cursor for file {file_path.name} to line {line_number}",
            extra={
                "source": self.source_name,
                "file_path": str(file_path),
                "line_number": line_number,
                "cursor_key": cursor_key,
            },
        )

    def _hash_file_path(self, file_path: Path) -> str:
        """Generate short hash for file path to use in Redis keys.

        Uses SHA-256 hash truncated to 16 characters for reasonable key length
        while avoiding collisions.

        Args:
            file_path: Path to hash

        Returns:
            16-character hex hash of file path

        Example:
            >>> reader._hash_file_path(Path("/home/user/.claude/session.jsonl"))
            'a1b2c3d4e5f6g7h8'
        """
        path_str = str(file_path.resolve())
        hash_obj = hashlib.sha256(path_str.encode("utf-8"))
        return hash_obj.hexdigest()[:16]
