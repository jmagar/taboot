"""Redis client wrapper for state management, deduplication, DLQ, and distributed locks.

This module provides a RedisClient class that handles:
1. Connection pooling and health checks
2. State management (cursors and content hashes for deduplication)
3. Dead Letter Queue (DLQ) operations using Redis Lists
4. Distributed locks with SETNX and TTL for preventing concurrent ingestion

Key naming conventions (from shared.md):
- hash:<source>:<doc_id> - Content hash for deduplication
- cursor:<source> - Last sync cursor/timestamp for incremental sync
- dlq:<source> - Dead letter queue for failed documents
- lock:ingest:<source> - Distributed lock to prevent duplicate ingestion jobs
"""

import json
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import redis
from redis.connection import ConnectionPool


class RedisClient:
    """Redis client for state management, deduplication, DLQ, and distributed locks.

    This class provides connection pooling and methods for:
    - State management (cursors for incremental sync)
    - Deduplication (content hash storage)
    - Dead letter queue operations
    - Distributed locking with auto-expiration

    Attributes:
        redis_url: Redis connection URL
        pool: Redis connection pool
        client: Redis client instance
    """

    def __init__(self, redis_url: str, max_connections: int = 50):
        """Initialize Redis client with connection pooling.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            max_connections: Maximum number of connections in the pool

        Raises:
            redis.ConnectionError: If unable to connect to Redis
        """
        self.redis_url = redis_url

        # Create connection pool for efficient connection management
        self.pool = ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=True,  # Automatically decode bytes to strings
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        # Create Redis client using the pool
        self.client = redis.Redis(connection_pool=self.pool)

    def health_check(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False

    def close(self) -> None:
        """Close all connections in the pool.

        Should be called when shutting down the application.
        """
        self.pool.disconnect()

    # =========================================================================
    # State Management Methods (Cursors)
    # =========================================================================

    def get_cursor(self, source: str) -> str | None:
        """Get the last sync cursor for incremental sync.

        Args:
            source: Source identifier (e.g., 'gmail', 'github', 'reddit')

        Returns:
            Cursor value or None if no previous sync

        Example:
            >>> cursor = redis_client.get_cursor('github')
            >>> if cursor:
            ...     # Fetch only items updated since cursor
        """
        key = f"cursor:{source}"
        # decode_responses=True ensures string return type
        return cast(str | None, self.client.get(key))

    def set_cursor(self, source: str, cursor: str) -> None:
        """Set the last sync cursor after successful sync.

        Args:
            source: Source identifier
            cursor: Cursor value (timestamp, historyId, etc.)

        Example:
            >>> redis_client.set_cursor('github', '2024-09-30T10:00:00Z')
        """
        key = f"cursor:{source}"
        self.client.set(key, cursor)

    # =========================================================================
    # Deduplication Methods (Content Hashes)
    # =========================================================================

    def get_hash(self, source: str, doc_id: str) -> str | None:
        """Get stored content hash for deduplication check.

        Args:
            source: Source identifier
            doc_id: Document ID

        Returns:
            SHA-256 content hash or None if not found

        Example:
            >>> stored_hash = redis_client.get_hash('gmail', 'msg_123')
            >>> if stored_hash == current_hash:
            ...     # Document unchanged, skip processing
        """
        key = f"hash:{source}:{doc_id}"
        # decode_responses=True ensures string return type
        return cast(str | None, self.client.get(key))

    def set_hash(self, source: str, doc_id: str, content_hash: str) -> None:
        """Store content hash for deduplication.

        Args:
            source: Source identifier
            doc_id: Document ID
            content_hash: SHA-256 hash of document content

        Example:
            >>> redis_client.set_hash('gmail', 'msg_123', computed_hash)
        """
        key = f"hash:{source}:{doc_id}"
        self.client.set(key, content_hash)

    def delete_hash(self, source: str, doc_id: str) -> None:
        """Delete stored content hash.

        Args:
            source: Source identifier
            doc_id: Document ID

        Example:
            >>> redis_client.delete_hash('github', 'repo/owner#123')
        """
        key = f"hash:{source}:{doc_id}"
        self.client.delete(key)

    # =========================================================================
    # Dead Letter Queue (DLQ) Methods
    # =========================================================================

    def push_to_dlq(self, source: str, doc_data: dict[str, Any], error: str) -> None:
        """Push failed document to Dead Letter Queue.

        Uses Redis Lists (LPUSH) for FIFO queue semantics.

        Args:
            source: Source identifier
            doc_data: Document data that failed processing
            error: Error message/traceback

        Example:
            >>> try:
            ...     process_document(doc)
            ... except Exception as e:
            ...     redis_client.push_to_dlq('gmail', doc, str(e))
        """
        key = f"dlq:{source}"

        dlq_entry = {
            "doc_data": doc_data,
            "error": error,
            "timestamp": time.time(),
            "source": source,
        }

        # Push to left (head) of list
        self.client.lpush(key, json.dumps(dlq_entry))

    def cleanup_dlq(self, source: str, retention_days: int) -> int:
        """Remove DLQ entries older than retention period.

        Args:
            source: Source identifier
            retention_days: Number of days to retain entries

        Returns:
            Number of entries removed

        Example:
            >>> # Remove entries older than 7 days
            >>> removed = redis_client.cleanup_dlq('gmail', retention_days=7)
            >>> print(f"Removed {removed} old DLQ entries")
        """
        key = f"dlq:{source}"

        # Calculate cutoff timestamp
        cutoff_time = time.time() - (retention_days * 86400)

        # Get all entries
        all_entries_json = self.client.lrange(key, 0, -1)

        # Filter entries to keep (newer than cutoff)
        entries_to_keep = []
        removed_count = 0

        for entry_json in all_entries_json:
            try:
                entry = json.loads(entry_json)
                entry_time = entry.get("timestamp", 0)

                if entry_time >= cutoff_time:
                    # Keep entry (within retention period)
                    entries_to_keep.append(entry_json)
                else:
                    # Entry is too old, will be removed
                    removed_count += 1

            except json.JSONDecodeError:
                # Skip malformed entries (they will be removed)
                removed_count += 1

        # Replace list with filtered entries
        if removed_count > 0:
            # Delete old list
            self.client.delete(key)

            # Re-create list with kept entries (if any)
            if entries_to_keep:
                # Push in reverse order to maintain FIFO semantics
                for entry_json in reversed(entries_to_keep):
                    self.client.rpush(key, entry_json)

        return removed_count

    def get_dlq(self, source: str, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve DLQ entries for inspection or reprocessing.

        Args:
            source: Source identifier
            limit: Maximum number of entries to retrieve

        Returns:
            List of DLQ entries with doc_data, error, and timestamp

        Example:
            >>> entries = redis_client.get_dlq('gmail', limit=10)
            >>> for entry in entries:
            ...     print(f"Error: {entry['error']}")
        """
        key = f"dlq:{source}"

        # Get entries from right (tail) of list (oldest first)
        entries_json = self.client.lrange(key, 0, limit - 1)

        entries = []
        for entry_json in entries_json:
            try:
                entries.append(json.loads(entry_json))
            except json.JSONDecodeError:
                # Skip malformed entries
                continue

        return entries

    def clear_dlq(self, source: str) -> int:
        """Clear all DLQ entries for a source.

        Args:
            source: Source identifier

        Returns:
            Number of entries cleared

        Example:
            >>> cleared = redis_client.clear_dlq('gmail')
            >>> print(f"Cleared {cleared} DLQ entries")
        """
        key = f"dlq:{source}"
        length = self.client.llen(key)
        self.client.delete(key)
        return length

    def get_dlq_size(self, source: str) -> int:
        """Get the number of entries in DLQ for a source.

        Args:
            source: Source identifier

        Returns:
            Number of DLQ entries

        Example:
            >>> size = redis_client.get_dlq_size('gmail')
            >>> if size > 100:
            ...     print("Warning: Large DLQ backlog")
        """
        key = f"dlq:{source}"
        return self.client.llen(key)

    # =========================================================================
    # Distributed Lock Methods
    # =========================================================================

    def acquire_lock(self, key: str, ttl: int = 300) -> str | None:
        """Acquire a distributed lock with automatic expiration.

        Uses SETNX (SET if Not eXists) with TTL to prevent deadlocks.

        Args:
            key: Lock key (e.g., 'ingest:gmail')
            ttl: Time-to-live in seconds (default: 5 minutes)

        Returns:
            Unique lock value if acquired, None if lock already held

        Example:
            >>> lock_value = redis_client.acquire_lock('ingest:gmail', ttl=600)
            >>> if lock_value:
            ...     try:
            ...         process_gmail_ingestion()
            ...     finally:
            ...         redis_client.release_lock('ingest:gmail', lock_value)
        """
        lock_key = f"lock:{key}"
        lock_value = str(uuid.uuid4())

        # Use SET with NX (not exists) and EX (expiration)
        acquired = self.client.set(lock_key, lock_value, nx=True, ex=ttl)

        if acquired:
            return lock_value
        return None

    def release_lock(self, key: str, lock_value: str) -> bool:
        """Release a distributed lock.

        Only releases if the lock is still owned by the caller (using lock_value).
        Uses Lua script for atomic check-and-delete.

        Args:
            key: Lock key
            lock_value: Unique value returned by acquire_lock

        Returns:
            True if lock was released, False if lock not owned

        Example:
            >>> lock_value = redis_client.acquire_lock('ingest:gmail')
            >>> if lock_value:
            ...     try:
            ...         # Critical section
            ...         pass
            ...     finally:
            ...         redis_client.release_lock('ingest:gmail', lock_value)
        """
        lock_key = f"lock:{key}"

        # Lua script for atomic check-and-delete
        # Only delete if value matches (prevents releasing someone else's lock)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        # Redis eval() is untyped in redis-py stubs but returns int in this case
        result = self.client.eval(lua_script, 1, lock_key, lock_value)  # type: ignore[no-untyped-call]
        return bool(result)

    def extend_lock(self, key: str, lock_value: str, additional_ttl: int = 300) -> bool:
        """Extend the TTL of an existing lock.

        Useful for long-running operations.

        Args:
            key: Lock key
            lock_value: Unique value returned by acquire_lock
            additional_ttl: Additional time in seconds

        Returns:
            True if lock was extended, False if lock not owned

        Example:
            >>> lock_value = redis_client.acquire_lock('ingest:gmail', ttl=60)
            >>> # ... long operation ...
            >>> redis_client.extend_lock('ingest:gmail', lock_value, additional_ttl=60)
        """
        lock_key = f"lock:{key}"

        # Lua script for atomic check-and-extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        # Redis eval() is untyped in redis-py stubs but returns int in this case
        result = self.client.eval(lua_script, 1, lock_key, lock_value, additional_ttl)  # type: ignore[no-untyped-call]
        return bool(result)

    @contextmanager
    def with_lock(
        self, key: str, ttl: int = 300, blocking_timeout: int = 0
    ) -> Generator[str | None, None, None]:
        """Context manager for distributed locks.

        Args:
            key: Lock key (e.g., 'ingest:gmail')
            ttl: Time-to-live in seconds (default: 5 minutes)
            blocking_timeout: Max seconds to wait for lock (0 = no wait)

        Yields:
            Lock value if acquired, None if not acquired

        Raises:
            TimeoutError: If lock not acquired within blocking_timeout (when > 0)

        Example:
            >>> with redis_client.with_lock('ingest:gmail', ttl=600) as lock:
            ...     if lock:
            ...         # Lock acquired, perform ingestion
            ...         process_gmail_ingestion()
            ...     else:
            ...         # Lock not acquired
            ...         print("Another process is already ingesting Gmail")
        """
        lock_value = None
        start_time = time.time()

        # Try to acquire lock (with optional blocking)
        while True:
            lock_value = self.acquire_lock(key, ttl)

            if lock_value:
                # Lock acquired
                break

            if blocking_timeout == 0:
                # Non-blocking mode, return None immediately
                break

            # Check timeout
            if time.time() - start_time >= blocking_timeout:
                if blocking_timeout > 0:
                    raise TimeoutError(f"Could not acquire lock '{key}' within {blocking_timeout}s")
                break

            # Wait briefly before retrying
            time.sleep(0.1)

        try:
            yield lock_value
        finally:
            # Always try to release lock if acquired
            if lock_value:
                self.release_lock(key, lock_value)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_all_sources_with_cursors(self) -> dict[str, str]:
        """Get all sources that have stored cursors.

        Returns:
            Dictionary mapping source names to cursor values

        Example:
            >>> sources = redis_client.get_all_sources_with_cursors()
            >>> for source, cursor in sources.items():
            ...     print(f"{source}: last synced at {cursor}")
        """
        # decode_responses=True ensures keys are strings
        cursor_keys = cast(list[str], self.client.keys("cursor:*"))
        result: dict[str, str] = {}

        for key in cursor_keys:
            # Extract source name from key (cursor:<source>)
            source = key.split(":", 1)[1]
            cursor_value = self.client.get(key)
            if cursor_value:
                # decode_responses=True ensures string return type
                result[source] = cast(str, cursor_value)

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get Redis client statistics.

        Returns:
            Dictionary with connection pool stats and key counts

        Example:
            >>> stats = redis_client.get_stats()
            >>> print(f"Cursors: {stats['cursor_count']}")
            >>> print(f"DLQ entries: {stats['dlq_total_size']}")
        """
        # Count different key types
        cursor_count = len(self.client.keys("cursor:*"))
        hash_count = len(self.client.keys("hash:*"))
        lock_count = len(self.client.keys("lock:*"))

        # Get DLQ sizes
        dlq_keys = self.client.keys("dlq:*")
        dlq_total = sum(self.client.llen(key) for key in dlq_keys)

        return {
            "cursor_count": cursor_count,
            "hash_count": hash_count,
            "lock_count": lock_count,
            "dlq_total_size": dlq_total,
            "pool_size": self.pool.max_connections,
            "healthy": self.health_check(),
        }

    def flush_all(self) -> None:
        """Flush all data from Redis.

        WARNING: This deletes ALL keys in the database. Use with caution!

        Example:
            >>> # Only use in testing or when resetting the system
            >>> redis_client.flush_all()
        """
        self.client.flushdb()
