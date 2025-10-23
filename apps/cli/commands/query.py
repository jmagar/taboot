"""CLI query command implementation."""

import os
from typing import Optional, List
from datetime import datetime
import typer
from rich.console import Console
from rich.panel import Panel
from packages.core.use_cases.query import execute_query


console = Console()


def query_command(
    question: str = typer.Argument(..., help="Question to answer"),
    sources: Optional[str] = typer.Option(None, help="Comma-separated source types (e.g., web,docker_compose)"),
    after: Optional[str] = typer.Option(None, help="Filter by ingestion date (ISO format: 2025-10-15)"),
    top_k: int = typer.Option(20, help="Number of candidates from vector search"),
    qdrant_url: Optional[str] = typer.Option(None, help="Qdrant URL (default from env)"),
    neo4j_uri: Optional[str] = typer.Option(None, help="Neo4j URI (default from env)"),
) -> None:
    """
    Query the knowledge base with natural language.

    Example:

        taboot query "Which services expose port 8080?"

        taboot query "Show all services" --sources web,docker_compose

        taboot query "Recent changes" --after 2025-10-15 --top-k 10
    """
    console.print(f"\n[bold blue]Query:[/bold blue] {question}\n")

    # Parse source types
    source_types: Optional[List[str]] = None
    if sources:
        source_types = [s.strip() for s in sources.split(",")]

    # Parse after date
    after_date: Optional[datetime] = None
    if after:
        try:
            after_date = datetime.fromisoformat(after)
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format: {after}")
            raise typer.Exit(1)

    # Get config from environment
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "changeme")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    try:
        # Execute query
        with console.status("[bold green]Retrieving and synthesizing answer..."):
            result = execute_query(
                query=question,
                qdrant_url=qdrant_url,
                neo4j_uri=neo4j_uri,
                neo4j_username=neo4j_user,
                neo4j_password=neo4j_password,
                ollama_base_url=ollama_url,
                top_k=top_k,
                source_types=source_types,
                after=after_date
            )

        if not result:
            console.print("[yellow]No results found.[/yellow]")
            return

        # Display answer
        answer = result.get("answer", "")
        console.print(Panel(answer, title="Answer", border_style="green"))

        # Display latency
        latency_ms = result.get("latency_ms", 0)
        breakdown = result.get("latency_breakdown", {})
        latency_str = f"[dim]Total: {latency_ms}ms"
        if breakdown:
            latency_str += f" (retrieval: {breakdown.get('retrieval_ms', 0)}ms, synthesis: {breakdown.get('synthesis_ms', 0)}ms)"
        latency_str += "[/dim]"
        console.print(latency_str)

        # Display stats
        vector_count = result.get("vector_count", 0)
        graph_count = result.get("graph_count", 0)
        console.print(f"[dim]Vector results: {vector_count}, Graph results: {graph_count}[/dim]\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)
