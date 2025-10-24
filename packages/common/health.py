"""Service health check utilities for Taboot platform.

Provides async health checks for all services (Neo4j, Qdrant, Redis, TEI, Ollama,
Firecrawl, Playwright) with proper timeout handling and error logging.

Required by FR-032: System MUST verify health of all services before reporting init success.
"""

import asyncio
from typing import TypedDict

import httpx
from neo4j import GraphDatabase
from redis import asyncio as redis

from packages.common.config import get_config
from packages.common.logging import get_logger

logger = get_logger(__name__)


class SystemHealthStatus(TypedDict):
    """System health status dictionary.

    Attributes:
        healthy: True if all services are healthy, False otherwise.
        services: Dictionary mapping service names to their health status.
    """

    healthy: bool
    services: dict[str, bool]


async def check_neo4j_health() -> bool:
    """Check Neo4j database health.

    Attempts to verify connectivity to Neo4j using the bolt driver.

    Returns:
        bool: True if Neo4j is healthy and responsive, False otherwise.
    """
    config = get_config()
    driver = None
    try:
        # Run synchronous Neo4j operations in executor to avoid blocking
        loop = asyncio.get_event_loop()
        driver = await loop.run_in_executor(
            None,
            lambda: GraphDatabase.driver(
                config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
            ),
        )
        await loop.run_in_executor(None, driver.verify_connectivity)
        logger.debug("Neo4j health check: OK")
        return True
    except Exception as e:
        logger.error("Neo4j health check failed", extra={"error": str(e)})
        return False
    finally:
        if driver:
            await asyncio.get_event_loop().run_in_executor(None, driver.close)


async def check_qdrant_health() -> bool:
    """Check Qdrant vector database health.

    Queries the Qdrant root endpoint for version info.

    Returns:
        bool: True if Qdrant is healthy and responsive, False otherwise.
    """
    config = get_config()
    try:
        async with httpx.AsyncClient(timeout=config.health_check_timeout) as client:
            response = await client.get(config.qdrant_url)
            healthy = response.status_code == 200
            if healthy:
                logger.debug("Qdrant health check: OK")
            else:
                logger.error(
                    "Qdrant health check failed",
                    extra={"status_code": response.status_code},
                )
            return healthy
    except Exception as e:
        logger.error("Qdrant health check failed", extra={"error": str(e)})
        return False


async def check_redis_health() -> bool:
    """Check Redis cache health.

    Attempts to ping Redis with timeout.

    Returns:
        bool: True if Redis is healthy and responsive, False otherwise.
    """
    config = get_config()
    client = None
    try:
        client = redis.from_url(
            config.redis_url,
            socket_timeout=config.health_check_timeout,
            decode_responses=True,
        )
        await client.ping()
        logger.debug("Redis health check: OK")
        return True
    except Exception as e:
        logger.error("Redis health check failed", extra={"error": str(e)})
        return False
    finally:
        if client:
            await client.aclose()


async def check_tei_health() -> bool:
    """Check TEI embedding service health.

    Queries the TEI /health endpoint with timeout.

    Returns:
        bool: True if TEI is healthy and responsive, False otherwise.
    """
    config = get_config()
    try:
        async with httpx.AsyncClient(timeout=config.health_check_timeout) as client:
            response = await client.get(f"{config.tei_embedding_url}/health")
            healthy = response.status_code == 200
            if healthy:
                logger.debug("TEI health check: OK")
            else:
                logger.error(
                    "TEI health check failed",
                    extra={"status_code": response.status_code},
                )
            return healthy
    except Exception as e:
        logger.error("TEI health check failed", extra={"error": str(e)})
        return False


async def check_ollama_health() -> bool:
    """Check Ollama LLM service health.

    Queries the Ollama /api/tags endpoint with timeout.

    Returns:
        bool: True if Ollama is healthy and responsive, False otherwise.
    """
    config = get_config()
    try:
        ollama_url = f"http://localhost:{config.ollama_port}"
        async with httpx.AsyncClient(timeout=config.health_check_timeout) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            healthy = response.status_code == 200
            if healthy:
                logger.debug("Ollama health check: OK")
            else:
                logger.error(
                    "Ollama health check failed",
                    extra={"status_code": response.status_code},
                )
            return healthy
    except Exception as e:
        logger.error("Ollama health check failed", extra={"error": str(e)})
        return False


async def check_firecrawl_health() -> bool:
    """Check Firecrawl web crawling service health.

    Queries the Firecrawl /health endpoint with timeout.

    Returns:
        bool: True if Firecrawl is healthy and responsive, False otherwise.
    """
    config = get_config()
    try:
        async with httpx.AsyncClient(timeout=config.health_check_timeout) as client:
            response = await client.get(f"{config.firecrawl_api_url}/health")
            healthy = response.status_code == 200
            if healthy:
                logger.debug("Firecrawl health check: OK")
            else:
                logger.error(
                    "Firecrawl health check failed",
                    extra={"status_code": response.status_code},
                )
            return healthy
    except Exception as e:
        logger.error("Firecrawl health check failed", extra={"error": str(e)})
        return False


async def check_playwright_health() -> bool:
    """Check Playwright browser service health.

    Queries the Playwright /health endpoint with timeout.

    Returns:
        bool: True if Playwright is healthy and responsive, False otherwise.
    """
    config = get_config()
    try:
        # Extract base URL from playwright_microservice_url (remove /scrape path)
        playwright_base_url = config.playwright_microservice_url.rsplit("/", 1)[0]
        async with httpx.AsyncClient(timeout=config.health_check_timeout) as client:
            response = await client.get(f"{playwright_base_url}/health")
            healthy = response.status_code == 200
            if healthy:
                logger.debug("Playwright health check: OK")
            else:
                logger.error(
                    "Playwright health check failed",
                    extra={"status_code": response.status_code},
                )
            return healthy
    except Exception as e:
        logger.error("Playwright health check failed", extra={"error": str(e)})
        return False


async def check_system_health() -> SystemHealthStatus:
    """Check health of all services in the Taboot platform.

    Runs all individual health checks concurrently with timeout handling.
    Returns aggregate status and per-service breakdown.

    Returns:
        SystemHealthStatus: Dictionary with 'healthy' (bool) and 'services' (dict[str, bool]).

    Example:
        >>> status = await check_system_health()
        >>> if status['healthy']:
        ...     print("All systems operational")
        >>> else:
        ...     failed = [s for s, h in status['services'].items() if not h]
        ...     print(f"Failed services: {failed}")
    """
    # Run all health checks concurrently
    results = await asyncio.gather(
        check_neo4j_health(),
        check_qdrant_health(),
        check_redis_health(),
        check_tei_health(),
        check_ollama_health(),
        check_firecrawl_health(),
        check_playwright_health(),
        return_exceptions=True,
    )

    # Map results to service names
    services = {
        "neo4j": bool(results[0]) if not isinstance(results[0], Exception) else False,
        "qdrant": bool(results[1]) if not isinstance(results[1], Exception) else False,
        "redis": bool(results[2]) if not isinstance(results[2], Exception) else False,
        "tei": bool(results[3]) if not isinstance(results[3], Exception) else False,
        "ollama": bool(results[4]) if not isinstance(results[4], Exception) else False,
        "firecrawl": bool(results[5]) if not isinstance(results[5], Exception) else False,
        "playwright": bool(results[6]) if not isinstance(results[6], Exception) else False,
    }

    # Overall health is True only if all services are healthy
    healthy = all(services.values())

    if healthy:
        logger.info("System health check: All services operational")
    else:
        failed = [name for name, status in services.items() if not status]
        logger.warning(
            "System health check: Some services failed",
            extra={"failed_services": failed},
        )

    return {"healthy": healthy, "services": services}


# Export public API
__all__ = [
    "SystemHealthStatus",
    "check_firecrawl_health",
    "check_neo4j_health",
    "check_ollama_health",
    "check_playwright_health",
    "check_qdrant_health",
    "check_redis_health",
    "check_system_health",
    "check_tei_health",
]
