"""CLI query command implementation."""

from __future__ import annotations

import os
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel

from packages.core.use_cases.query import execute_query

console = Console()


def query_command(
    question: str,
    sources: str | None = None,
    after: str | None = None,
    top_k: int = 20,
    qdrant_url: str | None = None,
    neo4j_uri: str | None = None,
) -> None:
    """Query the knowledge base with natural language.

    Example:

        taboot query "Which services expose port 8080?"

        taboot query "Show all services" --sources web,docker_compose

        taboot query "Recent changes" --after 2025-10-15 --top-k 10
    """
    console.print(f"\n[bold blue]Query:[/bold blue] {question}\n")

    # Parse source types
    source_types: list[str] | None = None
    if sources:
        source_types = [s.strip() for s in sources.split(",") if s.strip()]

    # Parse after date
    after_date: datetime | None = None
    if after:
        try:
            after_date = datetime.fromisoformat(after)
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid date format: {after}")
            raise typer.Exit(1) from None

    # Get config from environment - ensure all required strings are non-None
    resolved_qdrant_url: str = (
        qdrant_url if qdrant_url is not None else os.getenv("QDRANT_URL") or "http://localhost:4203"
    )
    resolved_neo4j_uri: str = (
        neo4j_uri if neo4j_uri is not None else os.getenv("NEO4J_URI") or "bolt://localhost:4206"
    )
    neo4j_user: str = os.getenv("NEO4J_USER") or "neo4j"
    neo4j_password: str = os.getenv("NEO4J_PASSWORD") or "changeme"
    qdrant_collection: str = os.getenv("COLLECTION_NAME") or "documents"
    tei_url: str = os.getenv("TEI_EMBEDDING_URL") or "http://localhost:4207"
    ollama_url: str = os.getenv("OLLAMA_BASE_URL") or "http://localhost:4214"
    reranker_url: str = os.getenv("RERANKER_URL") or "http://localhost:4208"
    reranker_timeout: float = float(os.getenv("RERANKER_TIMEOUT", "30"))
    reranker_model: str = os.getenv("RERANKER_MODEL") or "Qwen/Qwen3-Reranker-0.6B"
    reranker_device: str = os.getenv("RERANKER_DEVICE") or "auto"
    reranker_batch_size: int = int(os.getenv("RERANKER_BATCH_SIZE", "16"))

    try:
        # Execute query
        with console.status("[bold green]Retrieving and synthesizing answer..."):
            result = execute_query(
                query=question,
                qdrant_url=resolved_qdrant_url,
                qdrant_collection=qdrant_collection,
                neo4j_uri=resolved_neo4j_uri,
                neo4j_username=neo4j_user,
                neo4j_password=neo4j_password,
                tei_embedding_url=tei_url,
                ollama_base_url=ollama_url,
                reranker_url=reranker_url,
                reranker_timeout=reranker_timeout,
                reranker_model=reranker_model,
                reranker_device=reranker_device,
                reranker_batch_size=reranker_batch_size,
                top_k=top_k,
                source_types=source_types,
                after=after_date,
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
            retrieval_ms = breakdown.get("retrieval_ms", 0)
            synthesis_ms = breakdown.get("synthesis_ms", 0)
            latency_str += f" (retrieval: {retrieval_ms}ms, synthesis: {synthesis_ms}ms)"
        latency_str += "[/dim]"
        console.print(latency_str)

        # Display stats
        vector_count = result.get("vector_count", 0)
        graph_count = result.get("graph_count", 0)
        console.print(f"[dim]Vector results: {vector_count}, Graph results: {graph_count}[/dim]\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from None
