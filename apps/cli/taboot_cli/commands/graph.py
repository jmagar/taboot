"""CLI graph query command implementation.

Provides direct Cypher query execution against Neo4j for debugging
and exploration of the knowledge graph.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Literal

from neo4j.exceptions import Neo4jError
from rich.console import Console
from rich.table import Table

from packages.graph.client import Neo4jClient, Neo4jConnectionError

console = Console()


def query_command(
    cypher: str,
    output_format: Literal["table", "json"] = "table",
) -> None:
    """
    Execute a raw Cypher query against Neo4j.

    Examples:
        taboot graph query "MATCH (s:Service) RETURN s LIMIT 10"

        taboot graph query "MATCH (s:Service)-[r]->(h:Host)
            RETURN s.name, type(r), h.hostname LIMIT 5"

        taboot graph query "MATCH (n) RETURN count(n) as total_nodes" --format json
    """
    console.print(f"\n[bold blue]Executing Cypher query:[/bold blue]\n{cypher}\n")

    try:
        # Create Neo4j client and execute query
        with Neo4jClient() as client, client.session() as session:
            result = session.run(cypher)
            records = [record.data() for record in result]

        # Handle empty results
        if not records:
            console.print("[yellow]Query returned no results.[/yellow]")
            return

        # Format output
        if output_format == "json":
            console.print_json(json.dumps(records, indent=2, default=str))
        else:
            # Table format
            _display_table(records)

    except Neo4jConnectionError as e:
        console.print(f"[red]Connection error:[/red] {e}")
        sys.exit(1)
    except Neo4jError as e:
        console.print(f"[red]Neo4j error:[/red] {e}")
        console.print("\n[dim]Check your Cypher syntax and ensure the query is valid.[/dim]")
        sys.exit(1)


def _display_table(records: list[dict[str, Any]]) -> None:
    """Display query results as a Rich table.

    Args:
        records: List of record dictionaries from Neo4j query result.
    """
    if not records:
        return

    # Get all unique keys across all records
    keys = list(records[0].keys())

    # Create table
    table = Table(title=f"Query Results ({len(records)} rows)")

    # Add columns
    for key in keys:
        table.add_column(key, style="cyan", overflow="fold")

    # Add rows
    for record in records:
        row = []
        for key in keys:
            value = record.get(key)
            # Format value for display
            if value is None:
                row.append("[dim]null[/dim]")
            elif isinstance(value, dict):
                # Neo4j node/relationship - show properties
                row.append(json.dumps(value, default=str))
            elif isinstance(value, list | tuple):
                row.append(", ".join(str(v) for v in value))
            else:
                row.append(str(value))
        table.add_row(*row)

    console.print(table)
    console.print(f"\n[dim]Returned {len(records)} rows[/dim]\n")
