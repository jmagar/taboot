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
