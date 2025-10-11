"""Reader for Claude Code session files.

This module implements ClaudeCodeReader for parsing Claude Code JSONL conversation logs
stored in ~/.claude/projects/. The reader handles the Claude Code format which includes:

Format Structure:
    - type: Entry type (message, state, etc.)
    - uuid: Unique message identifier
    - message: Message content (string or structured object)
    - timestamp: ISO 8601 timestamp
    - sessionId: Conversation session identifier
    - cwd: Working directory path
    - gitBranch: Active git branch
    - userType: Role (user, assistant)
    - toolUseResult: Tool execution results

Document Creation:
    - doc_id: msg:{sessionId}:{line_number}
    - Extracts metadata: session_id, git_branch, working_directory, message_role, tools_used
    - Filters non-message entries
    - Handles both string and structured message formats

Usage:
    reader = ClaudeCodeReader(config=config, redis_client=redis_client)
    documents = reader.load_data(file_paths=[Path("~/.claude/projects/my-project/session.jsonl")])
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil.parser import parse as parse_datetime

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.sessions.base import SessionReader


class ClaudeCodeReader(SessionReader):
    """Reader for Claude Code JSONL session files.

    Parses Claude Code conversation logs with format:
    {
        "type": "message",
        "uuid": "msg-uuid",
        "message": "content string or object",
        "timestamp": "2025-10-10T14:32:00.000Z",
        "sessionId": "session-uuid",
        "cwd": "/path/to/project",
        "gitBranch": "main",
        "userType": "user" | "assistant",
        "toolUseResult": null | {...}
    }

    Creates message-level documents with:
    - doc_id: msg:{sessionId}:{line_number}
    - content: Raw message text
    - metadata: session_id, git_branch, working_directory, message_role, tools_used, etc.

    Attributes:
        source_name: Always "claude_code" for this reader
        config: Source configuration from config.yaml
        redis_client: Redis client for cursor management
    """

    def _parse_line(
        self,
        line_data: dict[str, Any],
        file_path: Path,
        line_number: int,
    ) -> Document | None:
        """Parse a Claude Code JSONL line into a Document.

        Args:
            line_data: Parsed JSON object from JSONL line
            file_path: Path to the JSONL file being processed
            line_number: 0-indexed line number in the file

        Returns:
            Document object if line is a message, None to skip non-message entries

        Raises:
            KeyError: If required fields are missing
            ValueError: If timestamp cannot be parsed
        """
        # Skip non-message entries
        entry_type = line_data.get("type")
        if entry_type != "message":
            self.logger.debug(
                f"Skipping non-message entry at line {line_number}",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "line_number": line_number,
                    "entry_type": entry_type,
                },
            )
            return None

        # Extract required fields
        try:
            session_id = line_data["sessionId"]
            message = line_data["message"]
            timestamp_str = line_data["timestamp"]
            user_type = line_data["userType"]
            cwd = line_data["cwd"]
        except KeyError as e:
            self.logger.warning(
                f"Missing required field in line {line_number}: {e}",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "line_number": line_number,
                    "missing_field": str(e),
                },
            )
            raise

        # Extract optional fields
        git_branch = line_data.get("gitBranch")
        tool_use_result = line_data.get("toolUseResult")

        # Handle both string and object message formats
        if isinstance(message, str):
            content = message
        elif isinstance(message, dict):
            # Stringify structured message objects
            content = json.dumps(message, ensure_ascii=False)
        else:
            # Fallback for unexpected types
            content = str(message)

        # Extract tool names from toolUseResult
        tools_used: list[str] = []
        if tool_use_result is not None:
            if isinstance(tool_use_result, dict):
                # toolUseResult may contain tool information
                # Extract tool name if present
                tool_name = tool_use_result.get("tool")
                if tool_name:
                    tools_used.append(tool_name)
            elif isinstance(tool_use_result, list):
                # Handle list of tool results
                for tool_result in tool_use_result:
                    if isinstance(tool_result, dict):
                        tool_name = tool_result.get("tool")
                        if tool_name:
                            tools_used.append(tool_name)

        # Parse timestamp
        try:
            timestamp = parse_datetime(timestamp_str)
        except Exception as e:
            self.logger.warning(
                f"Failed to parse timestamp '{timestamp_str}' in line {line_number}, using current time",
                extra={
                    "source": self.source_name,
                    "file_path": str(file_path),
                    "line_number": line_number,
                    "timestamp_str": timestamp_str,
                    "error": str(e),
                },
            )
            timestamp = datetime.now().astimezone()

        # Generate doc_id
        doc_id = f"msg:{session_id}:{line_number}"

        # Generate title with project basename
        project_name = os.path.basename(cwd) if cwd else "unknown"
        title = f"{user_type} message in {project_name}"

        # Generate content hash
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Build metadata extra dict
        extra: dict[str, Any] = {
            "session_id": session_id,
            "line_number": line_number,
            "working_directory": cwd,
            "message_role": user_type,
            "source_file": str(file_path.relative_to(Path.home())) if file_path.is_relative_to(Path.home()) else str(file_path),
        }

        # Add optional fields if present
        if git_branch:
            extra["git_branch"] = git_branch

        if tools_used:
            extra["tools_used"] = tools_used

        # Create metadata
        metadata = DocumentMetadata(
            source_type="claude_code",
            source_url=f"file://{file_path.resolve()}",
            timestamp=timestamp,
            extra=extra,
        )

        # Create and return document
        document = Document(
            doc_id=doc_id,
            title=title,
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )

        self.logger.debug(
            f"Parsed Claude Code message at line {line_number}",
            extra={
                "source": self.source_name,
                "file_path": str(file_path),
                "line_number": line_number,
                "doc_id": doc_id,
                "user_type": user_type,
                "tools_count": len(tools_used),
            },
        )

        return document
