"""Factories for shared CLI dependencies."""

from __future__ import annotations

from llamacrawl.config import Config
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient


def build_redis(config: Config) -> RedisClient:
    """Create a Redis client using CLI configuration."""
    return RedisClient(config.redis_url)


def build_qdrant(config: Config) -> QdrantClient:
    """Create a Qdrant client using CLI configuration."""
    return QdrantClient(
        url=config.qdrant_url,
        collection_name=config.vector_store.collection_name,
        vector_dimension=config.vector_store.vector_dimension,
        distance_metric=config.vector_store.distance_metric,
    )


def build_neo4j(config: Config) -> Neo4jClient:
    """Create a Neo4j client using CLI configuration."""
    return Neo4jClient(config=config)
