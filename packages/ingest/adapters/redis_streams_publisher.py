"""Redis Streams publisher for document ingestion events."""

from __future__ import annotations

from typing import Any

from redis import asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from packages.core.events import DocumentIngestedEvent
from packages.core.ports.event_publisher import DocumentEventPublisher


class RedisDocumentEventPublisher(DocumentEventPublisher):
    """Publish document lifecycle events to a Redis Stream."""

    def __init__(
        self,
        redis_client: Redis,
        stream_name: str = "stream:documents",
        *,
        maxlen: int | None = 1000,
    ) -> None:
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.maxlen = maxlen

    async def publish_document_ingested(self, event: DocumentIngestedEvent) -> None:
        payload: dict[str, Any] = {
            "event_type": "document_ingested",
            "doc_id": str(event.doc_id),
            "source_url": event.source_url,
            "chunk_count": str(event.chunk_count),
        }

        await self.redis_client.xadd(
            name=self.stream_name,
            fields=payload,
            maxlen=self.maxlen,
            approximate=True,
        )

    async def ensure_consumer_group(self, group_name: str) -> None:
        """Ensure a consumer group exists for the stream."""

        try:
            await self.redis_client.xgroup_create(
                name=self.stream_name,
                groupname=group_name,
                id="0-0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise


async def create_redis_client(url: str, *, decode_responses: bool = False) -> Redis:
    """Helper to create a Redis client from URL."""

    return redis.from_url(url, decode_responses=decode_responses)


__all__ = ["RedisDocumentEventPublisher", "create_redis_client"]
