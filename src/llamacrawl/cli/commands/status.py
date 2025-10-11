"""Status command module."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

import httpx
import typer

from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

from ..context import CLIState
from ..dependencies import build_neo4j, build_qdrant, build_redis

logger = get_logger(__name__)

VALID_SOURCES = ["firecrawl", "github", "reddit", "gmail", "elasticsearch"]


def status(
    ctx: typer.Context,
    source: Annotated[
        str | None,
        typer.Option(
            "--source",
            "-s",
            help=(
                "Show status for specific source "
                "(firecrawl, github, reddit, gmail, elasticsearch)"
            ),
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Display infrastructure and ingestion status."""
    state = ctx.ensure_object(CLIState)
    console = state.console
    config = state.config

    output_format = output_format.lower()
    if output_format not in {"text", "json"}:
        console.print(f"[bold red]Error:[/bold red] Invalid format '{output_format}'")
        console.print("Valid formats: text, json")
        raise typer.Exit(code=2)

    if source and source not in VALID_SOURCES:
        console.print(
            f"[bold red]Error:[/bold red] Invalid source '{source}'. "
            f"Valid sources: {', '.join(VALID_SOURCES)}"
        )
        raise typer.Exit(code=2)

    logger.info("Status command called", extra={"source": source, "format": output_format})

    status_data: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "storage": {},
        "sources": {},
    }

    redis_client: RedisClient | None = None
    qdrant_client: QdrantClient | None = None
    neo4j_client: Neo4jClient | None = None

    try:
        console.print("[bold]Checking service health...[/bold]")
        redis_healthy, redis_client = _check_redis(config)
        qdrant_healthy, qdrant_client = _check_qdrant(config)
        neo4j_healthy, neo4j_client = _check_neo4j(config)
        tei_embedding_healthy = _http_health_check(config.tei_embedding_url, "/health")
        tei_reranker_healthy = _http_health_check(config.tei_reranker_url, "/health")

        status_data["services"] = {
            "redis": {"healthy": redis_healthy, "url": config.redis_url},
            "qdrant": {"healthy": qdrant_healthy, "url": config.qdrant_url},
            "neo4j": {"healthy": neo4j_healthy, "url": config.neo4j_uri},
            "tei_embeddings": {"healthy": tei_embedding_healthy, "url": config.tei_embedding_url},
            "tei_reranker": {"healthy": tei_reranker_healthy, "url": config.tei_reranker_url},
        }

        console.print("[bold]Gathering storage statistics...[/bold]")
        status_data["storage"].update(
            _collect_storage_stats(
                config=config,
                qdrant_client=qdrant_client if qdrant_healthy else None,
                neo4j_client=neo4j_client if neo4j_healthy else None,
            )
        )

        console.print("[bold]Gathering source information...[/bold]")
        status_data["sources"] = _collect_source_info(
            config=config,
            redis_client=redis_client if redis_healthy else None,
            qdrant_counts=status_data["storage"].get("documents_per_source", {}),
            requested_source=source,
        )

        if output_format == "json":
            console.print_json(data=status_data)
        else:
            _render_text_output(console, status_data)

        logger.info("Status command completed successfully")

    except typer.Exit:
        raise
    except Exception as error:
        console.print(f"[bold red]Error retrieving status:[/bold red] {error}")
        logger.exception("Status command failed")
        raise typer.Exit(code=1) from error
    finally:
        if neo4j_client is not None:
            try:
                neo4j_client.close()
            except Exception:  # pragma: no cover - defensive
                logger.debug("Failed to close Neo4j client during status command")


def _check_redis(config: Any) -> tuple[bool, RedisClient | None]:
    try:
        client = build_redis(config)
        return client.health_check(), client
    except Exception as error:
        logger.error("Redis health check error: %s", error)
        return False, None


def _check_qdrant(config: Any) -> tuple[bool, QdrantClient | None]:
    try:
        client = build_qdrant(config)
        return client.health_check(), client
    except Exception as error:
        logger.error("Qdrant health check error: %s", error)
        return False, None


def _check_neo4j(config: Any) -> tuple[bool, Neo4jClient | None]:
    try:
        client = build_neo4j(config)
        return client.health_check(), client
    except Exception as error:
        logger.error("Neo4j health check error: %s", error)
        return False, None


def _http_health_check(url: str | None, endpoint: str) -> bool:
    if not url:
        return False
    try:
        full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else url
        response = httpx.get(full_url, timeout=5.0, follow_redirects=True)
        return response.status_code == 200
    except Exception as error:
        logger.debug("Health check failed for %s: %s", url, error)
        return False


def _collect_storage_stats(
    *,
    config: Any,
    qdrant_client: QdrantClient | None,
    neo4j_client: Neo4jClient | None,
) -> dict[str, Any]:
    storage: dict[str, Any] = {}

    if qdrant_client:
        try:
            storage["total_documents"] = qdrant_client.get_document_count()
            per_source: dict[str, int] = {}
            for src in VALID_SOURCES:
                count = qdrant_client.get_document_count(source_type=src)
                if count > 0:
                    per_source[src] = count
            storage["documents_per_source"] = per_source
        except Exception as error:
            logger.error("Failed to get Qdrant document counts: %s", error)
            storage["total_documents"] = 0
            storage["documents_per_source"] = {}
    else:
        storage["total_documents"] = 0
        storage["documents_per_source"] = {}

    if neo4j_client:
        try:
            storage["neo4j_nodes"] = neo4j_client.get_node_counts()
        except Exception as error:
            logger.error("Failed to get Neo4j node counts: %s", error)
            storage["neo4j_nodes"] = {}
    else:
        storage["neo4j_nodes"] = {}

    return storage


def _collect_source_info(
    *,
    config: Any,
    redis_client: RedisClient | None,
    qdrant_counts: dict[str, int],
    requested_source: str | None,
) -> dict[str, Any]:
    if not redis_client:
        return {}

    try:
        sources_with_cursors = redis_client.get_all_sources_with_cursors()
        sources_to_check = VALID_SOURCES if not requested_source else [requested_source]

        sources: dict[str, Any] = {}
        for src in sources_to_check:
            info = {
                "enabled": bool(getattr(config.sources, src).enabled),
                "last_sync": sources_with_cursors.get(src),
                "dlq_size": 0,
                "dlq_sample_errors": [],
                "document_count": qdrant_counts.get(src, 0),
            }

            dlq_size = redis_client.get_dlq_size(src)
            info["dlq_size"] = dlq_size

            if dlq_size > 0:
                dlq_entries = redis_client.get_dlq(src, limit=3)
                info["dlq_sample_errors"] = [
                    {
                        "error": _truncate_error(entry.get("error", "Unknown error")),
                        "timestamp": entry.get("timestamp"),
                    }
                    for entry in dlq_entries
                ]

            sources[src] = info

        return sources
    except Exception as error:
        logger.error("Failed to gather source information: %s", error)
        return {}


def _truncate_error(message: str, length: int = 100) -> str:
    return message if len(message) <= length else f"{message[:length]}..."


def _render_text_output(console: Any, status_data: dict[str, Any]) -> None:
    console.print("\n[bold cyan]LlamaCrawl System Status[/bold cyan]")
    console.print(f"Timestamp: {status_data['timestamp']}\n")

    console.print("[bold]Infrastructure Services:[/bold]")
    for name, service in status_data["services"].items():
        symbol = "[green]✓[/green]" if service["healthy"] else "[red]✗[/red]"
        display_name = name.replace("_", " ").title()
        console.print(f"  {symbol} {display_name}: {service['url']}")

    console.print("\n[bold]Storage Statistics:[/bold]")
    console.print(f"  Total Documents: {status_data['storage'].get('total_documents', 0)}")
    neo4j_nodes = status_data["storage"].get("neo4j_nodes") or {}
    if neo4j_nodes:
        console.print("  Neo4j Nodes:")
        for label, count in neo4j_nodes.items():
            console.print(f"    - {label}: {count}")

    console.print("\n[bold]Data Sources:[/bold]")
    sources = status_data.get("sources") or {}
    if not sources:
        console.print("  [dim]No source information available (Redis unavailable)[/dim]")
        console.print()
        return

    for name, info in sources.items():
        enabled = "[green]enabled[/green]" if info.get("enabled") else "[dim]disabled[/dim]"
        console.print(f"\n  [bold]{name.title()}[/bold] ({enabled})")
        console.print(f"    Documents: {info.get('document_count', 0)}")

        last_sync = info.get("last_sync")
        if last_sync:
            console.print(f"    Last Sync: {last_sync}")
        else:
            console.print("    Last Sync: [dim]Never ingested[/dim]")

        dlq_size = info.get("dlq_size", 0)
        if dlq_size > 0:
            console.print(f"    [yellow]DLQ Errors: {dlq_size}[/yellow]")
            sample_errors = info.get("dlq_sample_errors", [])
            if sample_errors:
                console.print("    Sample Errors:")
                for entry in sample_errors:
                    console.print(f"      - {entry['error']}")
        else:
            console.print("    DLQ Errors: [green]0[/green]")

    console.print()
