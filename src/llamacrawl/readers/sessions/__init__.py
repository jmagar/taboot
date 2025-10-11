"""Sessions reader module for AI coding assistant conversation logs.

This module provides readers for ingesting conversation logs from AI coding assistants
(Claude Code, Codex CLI) into LlamaCrawl's RAG pipeline.

Exports:
    SessionReader: Abstract base class for session file readers
    ClaudeCodeReader: Reader for Claude Code JSONL format
    CodexReader: Reader for Codex CLI JSONL format
    SessionsWatcher: File system watcher for real-time session monitoring
"""

from llamacrawl.readers.sessions.base import SessionReader

# Additional exports will be added as classes are implemented
__all__ = [
    "SessionReader",
    "ClaudeCodeReader",
    "CodexReader",
    "SessionsWatcher",
]
