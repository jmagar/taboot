"""Shared type definitions for the extraction package."""

from __future__ import annotations

from typing import TypedDict


class ExtractionWindow(TypedDict):
    """Represents a micro-window for Tier C LLM processing.

    Attributes:
        content: Window text content.
        token_count: Estimated token count.
        start: Start position in original text.
        end: End position in original text.
    """

    content: str
    token_count: int
    start: int
    end: int


class CodeBlock(TypedDict):
    """Represents a parsed code block from markdown.

    Attributes:
        language: Programming language identifier (e.g., "python", "javascript").
        code: Code content as string.
    """

    language: str
    code: str


class Table(TypedDict):
    """Represents a parsed markdown table.

    Attributes:
        headers: List of column header strings.
        rows: List of rows, where each row is a list of cell strings.
    """

    headers: list[str]
    rows: list[list[str]]
