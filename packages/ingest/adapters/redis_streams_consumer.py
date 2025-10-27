"""Redis Streams consumer for document ingestion events."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Awaitable, Callable, cast
from uuid import UUID

from redis.asyncio import Redis

from packages.core.events import DocumentIngestedEvent


class RedisDocumentEventConsumer:
    """Consume document ingestion events from Redis Streams."""

    def __init__(
        self,
        redis_client: Redis[Any],
        *,
        stream_name: str,
        group_name: str,
        consumer_name: str,
    ) -> None:
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name

    async def read(  # noqa: D401 - inherited behaviour
        self,
        *,
        count: int = 1,
        block_ms: int | None = 5000,
    ) -> list[tuple[str, DocumentIngestedEvent]]:
        """Read events from the stream as (message_id, event) tuples."""

        response = await self.redis_client.xreadgroup(
            groupname=self.group_name,
            consumername=self.consumer_name,
            streams={self.stream_name: ">"},
            count=count,
            block=block_ms,
        )

        events: list[tuple[str, DocumentIngestedEvent]] = []

        for stream_name, messages in response:
            stream = stream_name.decode() if isinstance(stream_name, bytes) else stream_name
            if stream != self.stream_name:
                continue
            for message_id, payload in messages:
                data = {
                    k.decode() if isinstance(k, bytes) else k: v.decode()
                    if isinstance(v, bytes)
                    else v
                    for k, v in payload.items()
                }
                event = DocumentIngestedEvent(
                    doc_id=UUID(data["doc_id"]),
                    source_url=data.get("source_url", ""),
                    chunk_count=int(data.get("chunk_count", 0)),
                )
                events.append(
                    (message_id.decode() if isinstance(message_id, bytes) else message_id, event)
                )

        return events

    async def ack(self, message_ids: Iterable[str]) -> None:
        """Acknowledge processed messages."""

        ids = list(message_ids)
        if not ids:
            return

        xack = cast(
            Callable[..., Awaitable[int]],
            getattr(self.redis_client, "xack"),
        )
        await xack(self.stream_name, self.group_name, *ids)


__all__ = ["RedisDocumentEventConsumer"]
