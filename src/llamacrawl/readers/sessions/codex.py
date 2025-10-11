"""Reader for Codex CLI session files.

This module implements CodexReader for parsing Codex CLI JSONL conversation logs
stored in ~/.codex/sessions/. The reader handles the Codex CLI format which includes:

Format Structure:
    - type: Entry type (message, state, etc.)
    - role: Message role (user, assistant, system)
    - content: Structured content array with type and text fields
    - timestamp: ISO 8601 timestamp
    - git: Nested git context (commit_hash, branch, repository_url)
    - id: Message identifier (used for session_id)
    - instructions: System instructions with working directory info

Session ID Extraction:
    - Parsed from filename: rollout-{timestamp}-{uuid}.jsonl
    - First entry contains metadata (git, instructions) cached for all messages

Document Creation:
    - doc_id: msg:{id}:{line_number}
    - Extracts metadata: commit_hash, branch, repository_url, working_directory
    - Filters non-message and state entries
    - Concatenates content array into single text string

Usage:
    reader = CodexReader(config=config, redis_client=redis_client)
    documents = reader.load_data(file_paths=[Path("~/.codex/sessions/rollout-123-abc.jsonl")])
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dateutil.parser import parse as parse_datetime

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.sessions.base import SessionReader
from llamacrawl.storage.redis import RedisClient


class CodexReader(SessionReader):
    """Reader for Codex CLI session files.

    Parses Codex CLI JSONL format with structured content arrays and nested git metadata.
    Caches git context and instructions from first entry (metadata entry) for use across
    all messages in the file.

    Attributes:
        source_name: Always "codex"
        config: Configuration dict from config.yaml
        redis_client: Redis client for cursor management
        _metadata_cache: Per-file cache of git context and instructions
    """

    def __init__(
        self,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize the Codex reader.

        Args:
            config: Source-specific configuration from config.yaml
            redis_client: Redis client instance for state management

        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__("codex", config, redis_client)
        # Cache for metadata extracted from first entry in each file
        # Key: file_path_hash, Value: dict with git context and working_directory
        self._metadata_cache: dict[str, dict[str, Any]] = {}

    def _parse_line(
        self,
        line_data: dict[str, Any],
        file_path: Path,
        line_number: int,
    ) -> Document | None:
        """Parse a single Codex CLI JSONL line into a Document.

        Args:
            line_data: Parsed JSON object from JSONL line
            file_path: Path to the JSONL file being processed
            line_number: 0-indexed line number in the file

        Returns:
            Document object if line should be ingested, None to skip

        Raises:
            ValueError: If required fields are missing from message entry
        """
        # Extract entry type and role
        entry_type = line_data.get("type")
        record_type = line_data.get("record_type")
        role = line_data.get("role")

        # Skip state/metadata entries (but cache their metadata first)
        if record_type == "state":
            self._cache_metadata_from_entry(line_data, file_path)
            return None

        # Skip non-message entries
        if entry_type != "message":
            return None

        # Cache metadata from first message entry if it has git/instructions
        if line_number == 0 or (line_data.get("git") or line_data.get("instructions")):
            self._cache_metadata_from_entry(line_data, file_path)

        # Extract required fields
        message_id = line_data.get("id")
        if not message_id:
            raise ValueError(f"Missing required field 'id' in message entry at line {line_number}")

        # Extract and concatenate content array
        content_array = line_data.get("content", [])
        if not isinstance(content_array, list):
            raise ValueError(f"Field 'content' must be a list at line {line_number}")

        content_text = self._concatenate_content_array(content_array)
        if not content_text:
            # Skip empty messages
            return None

        # Extract timestamp
        timestamp_str = line_data.get("timestamp")
        if not timestamp_str:
            # Use current time if no timestamp
            timestamp = datetime.now(timezone.utc)
            self.logger.warning(
                f"Missing timestamp in message at line {line_number}, using current time",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "line_number": line_number,
                },
            )
        else:
            timestamp = parse_datetime(timestamp_str)
            # Ensure timezone aware
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Get cached metadata for this file
        file_hash = self._hash_file_path(file_path)
        cached_metadata = self._metadata_cache.get(file_hash, {})

        # Extract session ID from filename
        session_id = self._extract_session_id(file_path)

        # Build document metadata
        git_branch = cached_metadata.get("git_branch")
        git_commit = cached_metadata.get("git_commit")
        git_repo = cached_metadata.get("git_repo")
        working_directory = cached_metadata.get("working_directory")

        # Create title using git context or working directory
        title_context = git_repo or working_directory or file_path.stem
        title = f"{role} message in {title_context}"

        # Compute content hash
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

        # Build extra metadata
        extra: dict[str, Any] = {
            "session_id": session_id,
            "line_number": line_number,
            "message_role": role,
            "source_file": str(file_path.relative_to(file_path.parent.parent.parent)),
        }

        # Add git context if available
        if git_branch:
            extra["git_branch"] = git_branch
        if git_commit:
            extra["git_commit"] = git_commit
        if git_repo:
            extra["git_repo"] = git_repo
        if working_directory:
            extra["working_directory"] = working_directory

        # Create document
        document = Document(
            doc_id=f"msg:{message_id}:{line_number}",
            title=title,
            content=content_text,
            content_hash=content_hash,
            metadata=DocumentMetadata(
                source_type="codex",
                source_url=f"file://{file_path.resolve()}",
                timestamp=timestamp,
                extra=extra,
            ),
        )

        return document

    def _cache_metadata_from_entry(
        self,
        line_data: dict[str, Any],
        file_path: Path,
    ) -> None:
        """Extract and cache metadata from entry.

        The first entry in Codex CLI files often contains git context and instructions
        that apply to all subsequent messages. This method caches that metadata.

        Args:
            line_data: Parsed JSON object from JSONL line
            file_path: Path to the JSONL file being processed
        """
        file_hash = self._hash_file_path(file_path)

        # Initialize cache for this file if not exists
        if file_hash not in self._metadata_cache:
            self._metadata_cache[file_hash] = {}

        cache = self._metadata_cache[file_hash]

        # Extract git context if present
        git_context = line_data.get("git")
        if git_context and isinstance(git_context, dict):
            if "branch" in git_context:
                cache["git_branch"] = git_context["branch"]
            if "commit_hash" in git_context or "commit" in git_context:
                cache["git_commit"] = git_context.get("commit_hash") or git_context.get("commit")
            if "repository_url" in git_context or "repo" in git_context:
                cache["git_repo"] = git_context.get("repository_url") or git_context.get("repo")

        # Extract working directory from instructions if present
        instructions = line_data.get("instructions")
        if instructions and isinstance(instructions, str):
            # Instructions may contain working directory information
            # Look for patterns like "Working directory: /path/to/dir"
            wd_match = re.search(r"(?:Working directory|CWD|working dir):\s*([^\n]+)", instructions, re.IGNORECASE)
            if wd_match:
                cache["working_directory"] = wd_match.group(1).strip()
        elif instructions and isinstance(instructions, dict):
            # Instructions might be a dict with working_directory field
            if "working_directory" in instructions:
                cache["working_directory"] = instructions["working_directory"]

        self.logger.debug(
            f"Cached metadata for file {file_path.name}",
            extra={
                "source": self.source_name,
                "file_path": str(file_path),
                "cached_fields": list(cache.keys()),
            },
        )

    def _concatenate_content_array(self, content_array: list[dict[str, Any]]) -> str:
        """Concatenate content array into single text string.

        Codex CLI format stores content as an array of objects with 'type' and 'text' fields.
        This method extracts and concatenates all text fields.

        Args:
            content_array: List of content objects from JSONL line

        Returns:
            Concatenated text from all content objects

        Example:
            >>> content = [
            ...     {"type": "input_text", "text": "How do I fix this?"},
            ...     {"type": "input_text", "text": "It's broken."}
            ... ]
            >>> reader._concatenate_content_array(content)
            "How do I fix this?\\nIt's broken."
        """
        text_parts: list[str] = []

        for content_obj in content_array:
            if not isinstance(content_obj, dict):
                continue

            # Extract text field
            text = content_obj.get("text")
            if text and isinstance(text, str):
                text_parts.append(text.strip())

        return "\n".join(text_parts)

    def _extract_session_id(self, file_path: Path) -> str:
        """Extract session ID from Codex CLI filename.

        Codex CLI files follow the pattern: rollout-{timestamp}-{uuid}.jsonl

        Args:
            file_path: Path to JSONL file

        Returns:
            Session UUID extracted from filename, or filename stem if pattern doesn't match

        Example:
            >>> reader._extract_session_id(Path("rollout-1234567890-abc123.jsonl"))
            "abc123"
        """
        filename = file_path.stem  # Remove .jsonl extension

        # Pattern: rollout-{timestamp}-{uuid}
        match = re.match(r"rollout-\d+-(.+)$", filename)
        if match:
            return match.group(1)

        # Fallback: use full filename stem as session ID
        self.logger.warning(
            f"Could not extract session ID from filename {file_path.name}, using full stem",
            extra={
                "source": self.source_name,
                "file_path": str(file_path),
            },
        )
        return filename
