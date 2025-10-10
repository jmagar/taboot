"""Query command module."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Iterable

import typer
from rich.console import Console
from rich.table import Table

from llamacrawl.embeddings.reranker import TEIRerank
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.models.document import QueryResult
from llamacrawl.query.engine import QueryEngine
from llamacrawl.query.synthesis import AnswerSynthesizer
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from ..dependencies import build_qdrant

logger = get_logger(__name__)

VALID_SOURCES = {"firecrawl", "github", "reddit", "gmail", "elasticsearch"}


def query(
    ctx: typer.Context,
    text: Annotated[
        str,
        typer.Argument(help="Query text to search for"),
    ],
    sources: Annotated[
        str | None,
        typer.Option(
            "--sources",
            help=(
                "Filter by source types "
                "(comma-separated: firecrawl,github,reddit,gmail,elasticsearch)"
            ),
        ),
    ] = None,
    after: Annotated[
        str | None,
        typer.Option(
            "--after",
            help="Filter documents after this date (YYYY-MM-DD or ISO 8601 format)",
        ),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(
            "--before",
            help="Filter documents before this date (YYYY-MM-DD or ISO 8601 format)",
        ),
    ] = None,
    top_k: Annotated[
        int | None,
        typer.Option(
            "--top-k",
            help="Number of candidates to retrieve (default from config)",
            min=1,
            max=100,
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--output-format",
            help="Output format: text (pretty-print) or json",
        ),
    ] = "text",
) -> None:
    """Execute a semantic query against the knowledge base."""
    state = ctx.ensure_object(CLIState)
    console = state.console
    config = state.config

    logger.info("Query command called", extra={"query": text})

    neo4j_client: Neo4jClient | None = None
    try:
        sources_filter = _parse_sources_option(sources, console)
        after_dt = _parse_date_option(after, "--after", console)
        before_dt = _parse_date_option(before, "--before", console)
        output_format = _normalize_output_format(output_format, console)

        qdrant_client = build_qdrant(config)
        neo4j_client = Neo4jClient(config=config)

        embed_model = TEIEmbedding(base_url=config.tei_embedding_url)
        reranker = TEIRerank(
            base_url=config.tei_reranker_url,
            top_n=config.query.rerank_top_n,
        )

        query_engine = QueryEngine(
            config=config,
            qdrant_client=qdrant_client,
            neo4j_client=neo4j_client,
            embed_model=embed_model,
            reranker=reranker,
        )
        synthesizer = AnswerSynthesizer(config)

        console.print("[bold]Executing query...[/bold]")
        logger.info(
            "Executing query",
            extra={
                "sources": sources_filter,
                "after": after_dt.isoformat() if after_dt else None,
                "before": before_dt.isoformat() if before_dt else None,
                "top_k": top_k,
            },
        )

        results = query_engine.query(
            query_text=text,
            sources=sources_filter,
            after=after_dt,
            before=before_dt,
            top_k=top_k,
        )

        retrieved = list(results["results"])
        metrics = results.get("metrics", {})

        if not retrieved:
            _handle_no_results(
                console=console,
                output_format=output_format,
                sources=sources_filter,
                after=after,
                before=before,
                metrics=metrics,
            )
            raise typer.Exit(code=0)

        if output_format == "text":
            query_result = _synthesize_streaming_answer(
                console=console,
                synthesizer=synthesizer,
                query_text=text,
                retrieved=retrieved,
                total_time_ms=metrics.get("total_time_ms"),
            )
        else:
            query_result = synthesizer.synthesize(query_text=text, retrieved_docs=retrieved)
            console.print(query_result.model_dump_json(indent=2))

        logger.info(
            "Query completed successfully",
            extra={
                "num_results": len(query_result.sources),
                "query_time_ms": query_result.query_time_ms,
            },
        )

    except typer.Exit:
        raise
    except Exception as error:
        console.print(f"\n[bold red]Error executing query:[/bold red] {error}")
        logger.exception("Query execution failed")
        raise typer.Exit(code=1) from error
    finally:
        if neo4j_client is not None:
            try:
                neo4j_client.close()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Failed to close Neo4j client cleanly")


def _parse_sources_option(option: str | None, console: Console) -> list[str] | None:
    if not option:
        return None
    sources = [value.strip() for value in option.split(",") if value.strip()]
    invalid = [value for value in sources if value not in VALID_SOURCES]
    if invalid:
        console.print(
            f"[bold red]Error:[/bold red] Invalid source types: {', '.join(invalid)}"
        )
        console.print(f"Valid sources: {', '.join(sorted(VALID_SOURCES))}")
        raise typer.Exit(code=2)
    return sources


def _parse_date_option(option: str | None, flag: str, console: Console) -> datetime | None:
    if not option:
        return None

    try:
        return _parse_date(option)
    except ValueError as error:
        console.print(f"[bold red]Error:[/bold red] Invalid {flag} date: {error}")
        console.print(
            "Use format: YYYY-MM-DD or ISO 8601 (e.g., 2025-01-01 or 2025-01-01T10:30:00Z)"
        )
        raise typer.Exit(code=2) from error


def _normalize_output_format(option: str, console: Console) -> str:
    normalized = option.lower()
    if normalized not in {"text", "json"}:
        console.print(f"[bold red]Error:[/bold red] Invalid output format: {option}")
        console.print("Valid formats: text, json")
        raise typer.Exit(code=2)
    return normalized


def _handle_no_results(
    *,
    console: Console,
    output_format: str,
    sources: list[str] | None,
    after: str | None,
    before: str | None,
    metrics: dict[str, Any],
) -> None:
    if output_format == "text":
        console.print("\n[yellow]No results found for your query.[/yellow]")
        if sources:
            console.print(f"Sources filter: {', '.join(sources)}")
        if after or before:
            console.print(f"Date range: {after or 'any'} to {before or 'any'}")
    else:
        payload = {
            "answer": "No results found for your query.",
            "sources": [],
            "query_time_ms": int(metrics.get("total_time_ms", 0)),
            "retrieved_docs": 0,
            "reranked_docs": 0,
        }
        console.print(json.dumps(payload, indent=2))


def _synthesize_streaming_answer(
    *,
    console: Console,
    synthesizer: AnswerSynthesizer,
    query_text: str,
    retrieved: Iterable[Any],
    total_time_ms: Any,
) -> QueryResult:
    console.print("\n[bold]Answer:[/bold]\n")

    answer_parts: list[str] = []
    for delta in synthesizer.stream_synthesize(query_text, retrieved):
        console.print(delta, end="")
        answer_parts.append(delta)

    console.print("\n")

    sources = synthesizer._create_source_attributions(
        retrieved,
        include_snippets=True,
    )
    result = QueryResult(
        answer="".join(answer_parts),
        sources=sources,
        query_time_ms=int(total_time_ms or 0),
        retrieved_docs=len(retrieved),
        reranked_docs=len(retrieved),
    )

    _display_sources_and_stats(result, console)
    return result


def _display_sources_and_stats(query_result: QueryResult, console: Console) -> None:
    console.print("\n[bold cyan]Sources:[/bold cyan]")
    if query_result.sources:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Score", justify="right", style="yellow")
        table.add_column("Timestamp", style="dim")

        for index, source in enumerate(query_result.sources, start=1):
            title = source.title
            display_title = title[:50] + "..." if len(title) > 50 else title
            timestamp = source.timestamp.strftime("%Y-%m-%d %H:%M") if source.timestamp else "-"
            table.add_row(
                str(index),
                display_title,
                source.source_type,
                f"{source.score:.3f}",
                timestamp,
            )

        console.print(table)
        console.print("\n[bold cyan]Snippets:[/bold cyan]")
        for index, source in enumerate(query_result.sources, start=1):
            console.print(f"\n[bold][{index}] {source.title}[/bold]")
            console.print(f"  {source.snippet}")
            if source.url:
                console.print(f"  [dim]{source.url}[/dim]")
    else:
        console.print("[dim]No sources found[/dim]")

    console.print("\n[bold]Query Statistics:[/bold]")
    console.print(f"  Retrieved: {query_result.retrieved_docs} documents")
    console.print(f"  Reranked: {query_result.reranked_docs} documents")
    console.print(f"  Query time: {query_result.query_time_ms}ms")


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    raise ValueError(
        f"Could not parse date '{date_str}'. Use YYYY-MM-DD or ISO 8601 format."
    )
