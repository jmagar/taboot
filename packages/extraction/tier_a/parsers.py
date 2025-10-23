"""Tier A deterministic parsers for code blocks, tables, and structured data."""

import json
import re
from typing import Any

import yaml


def parse_code_blocks(content: str) -> list[dict[str, str]]:
    """Extract fenced code blocks from markdown content.

    Args:
        content: Markdown text content.

    Returns:
        list[dict[str, str]]: List of code blocks with language and code.
            Each dict has keys: "language" and "code".
    """
    if not content:
        return []

    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)

    return [{"language": lang, "code": code.strip()} for lang, code in matches]


def parse_tables(content: str) -> list[dict[str, Any]]:
    """Extract markdown tables from content.

    Args:
        content: Markdown text content.

    Returns:
        list[dict[str, Any]]: List of tables with headers and rows.
            Each dict has keys: "headers" (list[str]) and "rows" (list[list[str]]).
    """
    if not content:
        return []

    tables: list[dict[str, Any]] = []
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

                    tables.append({"headers": headers, "rows": rows})
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
            return yaml.safe_load(content)
        elif format_type == "json":
            return json.loads(content)
        else:
            raise ValueError(f"Unknown format_type: {format_type}")
    except (yaml.YAMLError, json.JSONDecodeError, ValueError):
        return None
