"""Tier A deterministic parsers for code blocks, tables, and structured data."""

import json
import re
from typing import Any

import yaml

from packages.extraction.types import CodeBlock, Table


def parse_code_blocks(content: str) -> list[CodeBlock]:
    """Extract fenced code blocks from markdown content.

    Args:
        content: Markdown text content.

    Returns:
        list[CodeBlock]: List of code blocks with language and code.
    """
    if not content:
        return []

    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)

    return [CodeBlock(language=lang, code=code.strip()) for lang, code in matches]


def parse_tables(content: str) -> list[Table]:
    """Extract markdown tables from content.

    Args:
        content: Markdown text content.

    Returns:
        list[Table]: List of tables with headers and rows.
    """
    if not content:
        return []

    tables: list[Table] = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if line is a table row (starts and ends with |)
        if line.startswith("|") and line.endswith("|"):
            # Parse header
            headers = [cell.strip() for cell in line.strip("|").split("|")]

            # Check for separator line
            if i + 1 < len(lines):
                separator = lines[i + 1].strip()
                if re.match(r"^\|[\s\-|]+\|$", separator):
                    # Parse data rows
                    rows: list[list[str]] = []
                    j = i + 2
                    while j < len(lines):
                        row_line = lines[j].strip()
                        if row_line.startswith("|") and row_line.endswith("|"):
                            row = [cell.strip() for cell in row_line.strip("|").split("|")]
                            rows.append(row)
                            j += 1
                        else:
                            break

                    tables.append(Table(headers=headers, rows=rows))
                    i = j
                    continue

        i += 1

    return tables


def parse_yaml_json(content: str, format_type: str) -> dict[str, Any] | list[Any] | None:
    """Parse YAML or JSON content.

    Args:
        content: YAML or JSON text content.
        format_type: Either "yaml" or "json".

    Returns:
        dict | list | None: Parsed structure, or None if parsing fails.
    """
    if not content or not content.strip():
        return None

    try:
        if format_type == "yaml":
            result = yaml.safe_load(content)
            # yaml.safe_load can return various types; validate return type
            if isinstance(result, (dict, list)):
                return result
            return None
        elif format_type == "json":
            result = json.loads(content)
            # json.loads can return various types; validate return type
            if isinstance(result, (dict, list)):
                return result
            return None
        else:
            raise ValueError(f"Unknown format_type: {format_type}")
    except (yaml.YAMLError, json.JSONDecodeError, ValueError):
        return None
