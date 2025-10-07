import asyncio
import pickle

import redis
import redis.asyncio as aioredis

from llamacrawl.storage.redis import PickleableRedisKVStore


def test_picklable_redis_kv_store_round_trip() -> None:
    sync_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    async_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

    store = PickleableRedisKVStore(
        redis_uri="redis://localhost:6379",
        redis_client=sync_client,
        async_redis_client=async_client,
    )

    state = store.__getstate__()
    assert state["redis_url"] == "redis://localhost:6379"
    assert state["sync_connection_kwargs"]["host"] == "localhost"

    serialized = pickle.dumps(store)
    restored = pickle.loads(serialized)

    assert restored._redis_client is not sync_client
    assert restored._async_redis_client is not async_client
    assert restored._redis_client.connection_pool.connection_kwargs["port"] == 6379

    sync_client.close()
    restored._redis_client.close()
    asyncio.run(async_client.aclose())
    asyncio.run(restored._async_redis_client.aclose())
