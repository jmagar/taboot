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
