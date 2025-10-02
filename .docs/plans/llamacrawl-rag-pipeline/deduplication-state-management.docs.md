# Deduplication and State Management in RAG Pipelines with Redis

## Overview

This document provides comprehensive research findings on deduplication patterns, state management strategies, and incremental sync mechanisms for RAG (Retrieval-Augmented Generation) pipelines using Redis as the primary state store.

## Table of Contents

1. [Content Hashing Strategies](#content-hashing-strategies)
2. [Redis Patterns for State Management](#redis-patterns-for-state-management)
3. [Incremental Sync Strategies](#incremental-sync-strategies)
4. [Dead Letter Queue Patterns](#dead-letter-queue-patterns)
5. [Concurrency Control](#concurrency-control)
6. [Python Libraries and Implementation](#python-libraries-and-implementation)
7. [Code Examples](#code-examples)

---

## Content Hashing Strategies

### SHA-256 Hashing

**Key Characteristics:**
- **Deterministic**: Same input always produces the same hash
- **One-way**: Computationally infeasible to reverse
- **Collision-resistant**: Extremely unlikely for different inputs to produce the same hash
- **Fixed output**: Always produces 256-bit (64 hexadecimal character) hash

**Performance Considerations:**

SHA-256 is more CPU-intensive than alternatives like xxHash or BLAKE3. For a 6616 MiB file:
- SHA-256: ~27 seconds
- xxHash: ~0.5 seconds

**When to Use:**
- When cryptographic security is required
- For long-term data integrity verification
- When hash collisions must be virtually impossible

**Alternatives:**
- **BLAKE3** (2020): Faster than SHA-256, cryptographically secure
- **xxHash**: Much faster but not cryptographically secure (use when adversaries are not a concern)
- **MD5**: Deprecated due to collision vulnerabilities, avoid for security-critical applications

**Sources:**
- https://levelup.gitconnected.com/harnessing-python-and-sha-256-an-intuitive-guide-to-removing-duplicate-files-d3b02e0b3978
- https://jolynch.github.io/posts/use_fast_data_algorithms/
- https://stackoverflow.com/questions/11696403/what-are-some-of-the-best-hashing-algorithms-to-use-for-data-integrity-and-dedup

### Content Normalization Before Hashing

**Critical preprocessing steps to ensure consistent hash generation:**

#### Text Normalization
1. **Whitespace normalization**: Remove duplicate spaces, tabs, and newlines
2. **Case normalization**: Convert all text to lowercase
3. **Punctuation handling**: Remove or standardize punctuation
4. **Accent removal**: Normalize accented characters (e.g., é → e)
5. **Contraction expansion**: Convert contractions (e.g., "I'm" → "I am")
6. **Special character removal**: Strip or normalize special characters

#### Email-Specific Normalization
For email address deduplication:
- Convert to lowercase
- Remove periods in Gmail addresses (user.name@gmail.com → username@gmail.com)
- Remove content after + (username+tag@gmail.com → username@gmail.com)
- Trim whitespace

#### Document-Specific Normalization
- **Tokenization**: Break text into manageable units
- **Lemmatization**: Reduce words to base forms (running → run)
- **Stemming**: Reduce words to root forms
- **Stop word removal**: Remove common words (the, is, at) to focus on informative content

**Sources:**
- https://www.narrative.io/knowledge-base/how-to-guides/how-to-normalize-emails-prior-to-hashing
- https://towardsdatascience.com/text-normalization-7ecc8e084e31/
- https://developer.nvidia.com/blog/mastering-llm-techniques-data-preprocessing/

### Hash Comparison Strategies

#### Exact Deduplication
- Generate hash signatures for each document
- Group documents by their hashes into buckets
- Keep only one document per bucket
- Use Redis Sets for O(1) membership checking

#### Fuzzy Deduplication
For near-duplicate detection:
- **MinHash signatures**: Generate multiple hash signatures per document
- **Locality-Sensitive Hashing (LSH)**: Group similar documents into buckets
- **Cosine similarity**: Compare vector representations for semantic similarity

**Workflow:**
1. **Shingling**: Tokenize document into n-grams
2. **Fingerprinting**: Generate MinHash signatures
3. **LSH bucketing**: Group similar documents
4. **Duplicate removal**: Keep one representative per group

**Sources:**
- https://wenjingzhan.medium.com/data-preprocessing-deduplication-with-minhash-and-lsh-99c5e10703d
- https://huggingface.co/blog/dedup
- https://github.com/ChenghaoMou/text-dedup

---

## Redis Patterns for State Management

### Key Naming Conventions

**Best Practices (2024):**

#### Standard Delimiter
Use colon (`:`) as the standard delimiter for hierarchical key structures:
```
object-type:id:field
user:1000:profile
session:user:1000:abc123
cache:document:hash:abc123...
```

#### Namespace Prefixes
Group related keys with consistent prefixes:
- `user:` - User-related data
- `session:` - Session data
- `cache:` - Cached items
- `temp:` - Temporary/short-lived data
- `dlq:` - Dead letter queue items
- `lock:` - Distributed locks
- `cursor:` - Pagination cursors
- `hash:` - Content hashes for deduplication

#### Design Principles
1. **Hierarchical structure**: Reflect relationships (e.g., `user:123:profile`)
2. **Descriptive names**: Balance brevity with clarity
3. **Include identifiers**: Make keys unique and traceable
4. **Mark temporary data**: Use prefixes like `temp:` or `cache:`
5. **Lowercase convention**: Avoid case sensitivity issues
6. **Reasonable size**: Avoid very short (e11r) or very long keys

**Memory Impact:**
Storing 1,000,000 keys with 32-character values:
- 6-character key names: 96MB
- 12-character key names: 111MB
- Overhead: 15% difference

**Sources:**
- https://dev.to/rijultp/redis-naming-conventions-every-developer-should-know-1ip
- https://medium.com/nerd-for-tech/unveiling-the-art-of-redis-key-naming-best-practices-6e20f3839e4a
- https://stackoverflow.com/questions/6965451/redis-key-naming-conventions

### Data Structures for Deduplication

#### Redis Sets (SADD, SISMEMBER)
**Best for**: Exact hash deduplication

**Characteristics:**
- Unordered collections of unique strings
- O(1) time complexity for add, remove, and membership testing
- Memory overhead: ~40 bytes per member

**Use case**: Store content hashes for exact duplicate detection

**Example key structure:**
```
hash:seen:documents          # Set of all document hashes
hash:seen:chunks             # Set of all chunk hashes
hash:source:gmail            # Hashes from Gmail source
hash:source:github           # Hashes from GitHub source
```

#### Redis Hashes (HSET, HGET)
**Best for**: Storing metadata with content hashes

**Characteristics:**
- More memory-efficient than individual SET keys (~56% memory savings)
- Small hashes use optimized ziplist encoding
- O(1) lookup by field

**Use case**: Store hash → metadata mappings

**Example key structure:**
```
doc:metadata:abc123hash      # HSET with fields: source, timestamp, url, size
chunk:metadata:def456hash    # HSET with fields: doc_id, position, tokens
```

#### Redis Sorted Sets (ZADD)
**Best for**: Time-ordered hash tracking

**Characteristics:**
- Members with associated scores (timestamps)
- O(log N) operations
- Higher memory overhead (~40 bytes per member-score pair)

**Use case**: Track when documents were first seen, expire old entries

**Example key structure:**
```
hash:timeline:documents      # ZADD score=timestamp, member=hash
hash:timeline:chunks         # Chronologically ordered chunk hashes
```

#### Redis Bloom Filters
**Best for**: Memory-efficient probabilistic deduplication

**Characteristics:**
- Probabilistic data structure (configurable false positive rate)
- Can guarantee absence but not presence
- **Memory savings**: ~92-98% compared to Sets
- Only stores hashed representations, not actual values

**Trade-offs:**
- False positives possible (configurable error rate)
- Cannot retrieve original values
- No false negatives (if it says "not present", it's definitely not present)

**Use case**: Pre-filter expensive operations, check if document likely seen before

**Example key structure:**
```
bloom:documents              # Bloom filter for document hashes
bloom:chunks                 # Bloom filter for chunk hashes
```

**RedisBloom Commands:**
- `BF.ADD key item` - Add item to filter
- `BF.EXISTS key item` - Check if item exists (may have false positives)
- `BF.MADD key item1 item2 ...` - Add multiple items
- `BF.MEXISTS key item1 item2 ...` - Check multiple items

**Sources:**
- https://redis.io/solutions/deduplication/
- https://redis.io/docs/latest/develop/data-types/probabilistic/bloom-filter/
- https://dip-mazumder.medium.com/redis-bloom-filters-how-i-scaled-a-memory-efficient-uniqueness-check-bd0e24bfaf7

**Memory Comparison:**
| Data Structure | Memory per Item | Accuracy | Use Case |
|---------------|-----------------|----------|----------|
| Set | ~40 bytes | 100% | Small-medium datasets, exact matching |
| Hash | ~20-30 bytes | 100% | Metadata storage with hash keys |
| Sorted Set | ~40 bytes | 100% | Time-ordered tracking |
| Bloom Filter | ~1-2 bytes | 98-99%+ | Large datasets, pre-filtering |

### Data Structures for Cursors and State

#### Simple String Keys
**Best for**: Single cursor values per source

```
cursor:gmail:user123         # SET/GET string value
cursor:github:repo456        # SET/GET string value
```

#### Hash Tables
**Best for**: Multiple cursors per source with metadata

```
cursor:state:gmail           # HSET fields: user123_cursor, user123_timestamp, user123_status
cursor:state:github          # HSET fields: repo456_cursor, repo456_timestamp, repo456_status
```

#### Sorted Sets for Cursor Priority
**Best for**: Tracking sync priority and scheduling

```
cursor:priority:sources      # ZADD score=last_sync_timestamp, member=source_id
```

### Data Structures for Dead Letter Queues

#### Redis Lists (LPUSH, RPOP, BRPOP)
**Best for**: FIFO queue operations

**Characteristics:**
- O(1) push/pop operations at both ends
- Blocking operations available (BRPOP)
- Natural queue semantics

**Use case**: Store failed messages for reprocessing

**Example key structure:**
```
dlq:failed:gmail             # List of failed Gmail ingestion jobs
dlq:failed:github            # List of failed GitHub ingestion jobs
dlq:processing:temp          # Temporary processing queue
```

#### Redis Streams
**Best for**: Advanced DLQ with consumer groups and delivery tracking

**Characteristics:**
- Built-in delivery counter
- Consumer groups for parallel processing
- Message claiming for reliability
- Automatic ID generation with timestamps

**Use case**: Reliable queue with retry tracking and parallel consumers

**Example key structure:**
```
stream:dlq:main              # Main DLQ stream
stream:dlq:parking           # Parking lot for permanent failures
```

**Sources:**
- https://stackoverflow.com/questions/50590339/is-it-possible-to-do-dead-letter-queue-using-redis
- https://dev.to/faranmustafa/implementing-a-reliable-event-driven-system-with-dead-letter-queues-in-golang-and-redis-43pb
- https://medium.com/bitso-engineering/the-redis-streams-we-have-known-and-loved-e9e596d49a22

---

## Incremental Sync Strategies

### Cursor-Based Pagination

#### Redis SCAN Pattern
**How it works:**
- SCAN is completely stateless (no server-side memory)
- Returns cursor for next iteration
- Cursor bits are reversed, incremented, then reversed again
- Guarantees eventual completion without duplicates (if dataset doesn't change)

**Implementation pattern:**
```python
cursor = 0
while True:
    cursor, keys = redis.scan(cursor=cursor, match='pattern:*', count=100)
    process_keys(keys)
    if cursor == 0:
        break
```

**Sources:**
- https://stackoverflow.com/questions/28102173/redis-how-does-scan-cursor-state-management-work
- https://redis.io/docs/latest/commands/ft.cursor-read/

#### Application-Level Cursors
For API pagination, store cursor state in Redis:

**Simple cursor storage:**
```python
# Store cursor after successful sync
redis.set('cursor:source:identifier', cursor_value)

# Retrieve cursor before next sync
cursor = redis.get('cursor:source:identifier') or '0'
```

**Cursor with metadata:**
```python
# Store cursor with timestamp and status
redis.hset('cursor:state:gmail', mapping={
    'cursor': history_id,
    'timestamp': datetime.now().isoformat(),
    'last_message_count': 150,
    'status': 'success'
})

# Retrieve cursor state
state = redis.hgetall('cursor:state:gmail')
cursor = state.get('cursor')
```

### Timestamp Tracking

#### Last Modified Tracking
Store timestamp of last successful sync:

```python
# After successful sync
redis.set('sync:timestamp:github:repo123', datetime.now().isoformat())

# Before next sync
last_sync = redis.get('sync:timestamp:github:repo123')
if last_sync:
    # Fetch only items modified after last_sync
    params = {'since': last_sync}
```

#### Sorted Set for Time-Based Sync
Track multiple sources by last sync time:

```python
# Update last sync time (score = timestamp)
redis.zadd('sync:schedule:sources', {
    'gmail:user123': time.time(),
    'github:repo456': time.time()
})

# Get sources that need syncing (oldest first)
sources_to_sync = redis.zrange('sync:schedule:sources', 0, 10)

# Get sources not synced in last hour
one_hour_ago = time.time() - 3600
stale_sources = redis.zrangebyscore('sync:schedule:sources', 0, one_hour_ago)
```

### Source-Specific Approaches

#### Gmail historyId Pattern

**How it works:**
- Gmail assigns incremental historyId to each mailbox change
- historyIds are chronological but not contiguous (random gaps)
- Use `history.list()` to get changes since last historyId

**Implementation pattern:**
```python
# Initial full sync
messages = gmail.users().messages().list(userId='me', maxResults=100).execute()
latest_message = messages['messages'][0]
latest_history_id = latest_message['historyId']

# Store history ID
redis.set('cursor:gmail:user123:historyid', latest_history_id)

# Incremental sync (triggered by push notification or polling)
stored_history_id = redis.get('cursor:gmail:user123:historyid')
history = gmail.users().history().list(
    userId='me',
    startHistoryId=stored_history_id
).execute()

# Process history changes
for record in history.get('history', []):
    # Handle messagesAdded, messagesDeleted, labelsAdded, etc.
    process_history_record(record)

# Update stored history ID
new_history_id = history.get('historyId', stored_history_id)
redis.set('cursor:gmail:user123:historyid', new_history_id)
```

**Key characteristics:**
- historyId is guaranteed to be monotonically increasing
- Push notifications (Pub/Sub) trigger incremental sync
- Stale historyId requires full sync
- Store historyId of most recent message after each sync

**Sources:**
- https://developers.google.com/gmail/api/guides/sync
- https://stackoverflow.com/questions/76573857/what-increments-a-historyid-in-gmail-api
- https://stackoverflow.com/questions/42987556/gmail-api-historyid-is-it-guaranteed-to-be-monotonic

#### GitHub Since Parameter Pattern

**How it works:**
- Many GitHub API endpoints support `since` parameter (ISO 8601 timestamp)
- Filters results to items updated after specified date
- Combine with pagination for complete incremental sync

**Implementation pattern:**
```python
# Store last sync timestamp
last_sync = redis.get('sync:timestamp:github:repo456')

# Fetch issues updated since last sync
params = {
    'since': last_sync or '1970-01-01T00:00:00Z',
    'state': 'all',
    'sort': 'updated',
    'direction': 'desc',
    'per_page': 100
}

page = 1
while True:
    params['page'] = page
    response = github_api.get('/repos/owner/repo/issues', params=params)
    issues = response.json()

    if not issues:
        break

    for issue in issues:
        # Stop if we've seen this issue before (optimization)
        if issue['updated_at'] <= last_sync:
            break

        process_issue(issue)

    page += 1

# Update last sync timestamp
redis.set('sync:timestamp:github:repo456', datetime.now().isoformat())
```

**Optimization strategies:**
1. **Sort descending**: Process newest items first, stop when crossing timestamp boundary
2. **Cursor storage**: Store page number or next URL for resumable sync
3. **Rate limit handling**: Store rate limit reset time in Redis

**Key GitHub API parameters:**
- `since`: ISO 8601 timestamp for filtering
- `per_page`: Results per page (default 30, max 100)
- `page`: Page number for pagination
- Link header: Contains URLs for next, prev, first, last pages

**Sources:**
- https://docs.github.com/rest/guides/using-pagination-in-the-rest-api
- https://towardsdatascience.com/3-essential-questions-to-address-when-building-an-api-involved-incremental-data-loading-script-03723cad3411/

#### Generic Incremental Sync Pattern

**For APIs without native cursor support:**

```python
# Hybrid approach: timestamp + offset tracking
sync_state = redis.hgetall('cursor:state:source123')
last_timestamp = sync_state.get('timestamp', '1970-01-01T00:00:00Z')
last_offset = int(sync_state.get('offset', 0))

# Fetch with filters
results = api.fetch(
    modified_after=last_timestamp,
    offset=last_offset,
    limit=100
)

# Process results
for item in results:
    process_item(item)

# Update state
redis.hset('cursor:state:source123', mapping={
    'timestamp': results[-1]['modified_at'] if results else last_timestamp,
    'offset': last_offset + len(results),
    'last_sync': datetime.now().isoformat()
})
```

---

## Dead Letter Queue Patterns

### Reliable Queue Pattern

**Concept**: Task not removed from queue immediately; moved to temporary queue until confirmed processed.

**Implementation with Redis Lists:**

```python
# Producer: Add message to main queue
redis.lpush('queue:main', json.dumps(message))

# Consumer: Move to processing queue atomically
message_json = redis.brpoplpush('queue:main', 'queue:processing', timeout=5)
if message_json:
    message = json.loads(message_json)

    try:
        process_message(message)
        # Success: Remove from processing queue
        redis.lrem('queue:processing', 1, message_json)
    except Exception as e:
        # Failure: Move to DLQ
        redis.lrem('queue:processing', 1, message_json)
        redis.lpush('dlq:failed', json.dumps({
            'message': message,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'attempts': message.get('attempts', 0) + 1
        }))
```

### TTL Management

#### Automatic Expiration with EXPIRE
```python
# Add message to DLQ with 7-day TTL
dlq_key = f'dlq:message:{message_id}'
redis.set(dlq_key, json.dumps(message))
redis.expire(dlq_key, 7 * 24 * 3600)  # 7 days in seconds

# Or atomically with SETEX
redis.setex(dlq_key, 7 * 24 * 3600, json.dumps(message))
```

#### Time-Based Cleanup with Sorted Sets
```python
# Store DLQ messages with timestamp score
redis.zadd('dlq:timeline', {
    json.dumps(message): time.time()
})

# Periodic cleanup of old messages (> 7 days)
seven_days_ago = time.time() - (7 * 24 * 3600)
expired = redis.zrangebyscore('dlq:timeline', 0, seven_days_ago)
if expired:
    redis.zremrangebyscore('dlq:timeline', 0, seven_days_ago)
```

### Reprocessing Patterns

#### Retry with Exponential Backoff
```python
def process_dlq_message(message_json):
    message = json.loads(message_json)
    attempts = message.get('attempts', 0)
    max_attempts = 5

    if attempts >= max_attempts:
        # Move to parking lot (permanent failure)
        redis.lpush('dlq:parking', json.dumps(message))
        return

    # Calculate backoff delay
    backoff_seconds = 2 ** attempts  # 1, 2, 4, 8, 16 seconds

    # Schedule retry
    retry_time = time.time() + backoff_seconds
    redis.zadd('dlq:scheduled_retries', {
        json.dumps(message): retry_time
    })

# Worker: Process scheduled retries
def process_scheduled_retries():
    now = time.time()
    ready = redis.zrangebyscore('dlq:scheduled_retries', 0, now)

    for message_json in ready:
        message = json.loads(message_json)
        try:
            process_message(message)
            # Success: Remove from scheduled retries
            redis.zrem('dlq:scheduled_retries', message_json)
        except Exception as e:
            # Failure: Update attempts and reschedule
            message['attempts'] = message.get('attempts', 0) + 1
            redis.zrem('dlq:scheduled_retries', message_json)
            process_dlq_message(json.dumps(message))
```

#### Error Classification Pattern
```python
class ErrorType:
    TRANSIENT = 'transient'      # Retry possible (network error, rate limit)
    NON_TRANSIENT = 'permanent'  # Retry futile (poison pill, validation error)

def handle_processing_error(message, error):
    error_type = classify_error(error)

    if error_type == ErrorType.NON_TRANSIENT:
        # Poison pill: Move directly to parking lot
        redis.lpush('dlq:parking', json.dumps({
            'message': message,
            'error': str(error),
            'error_type': 'poison_pill',
            'timestamp': datetime.now().isoformat()
        }))
    else:
        # Transient error: Move to retry queue
        message['attempts'] = message.get('attempts', 0) + 1
        redis.lpush('dlq:retry', json.dumps(message))

def classify_error(error):
    # Example classification logic
    if isinstance(error, (ValidationError, ValueError)):
        return ErrorType.NON_TRANSIENT
    elif isinstance(error, (ConnectionError, TimeoutError, RateLimitError)):
        return ErrorType.TRANSIENT
    else:
        return ErrorType.TRANSIENT  # Default to transient for safety
```

### DLQ Message Structure
```python
dlq_message = {
    'id': str(uuid.uuid4()),
    'original_message': {...},
    'error': str(exception),
    'error_type': 'transient|permanent',
    'stack_trace': traceback.format_exc(),
    'attempts': 3,
    'first_failed_at': '2024-01-15T10:30:00Z',
    'last_failed_at': '2024-01-15T10:35:00Z',
    'source': 'gmail|github|slack',
    'operation': 'ingest_email|fetch_issues',
    'metadata': {
        'source_id': 'msg_abc123',
        'user_id': 'user_456'
    }
}
```

**Sources:**
- https://www.redpanda.com/blog/reliable-message-processing-with-dead-letter-queue
- https://medium.com/eleveo-techblog/dead-letter-queue-reprocessing-a2c041f64e65
- https://dev.to/faranmustafa/implementing-a-reliable-event-driven-system-with-dead-letter-queues-in-golang-and-redis-43pb

---

## Concurrency Control

### Distributed Locks with Redis

#### Basic Lock Properties

**Safety Property**: Mutual exclusion - only one client can hold a lock at any moment.

**Liveness Property**: Deadlock-free - eventually always possible to acquire lock, even if client crashes.

#### SETNX Pattern (Basic Lock)
```python
# Acquire lock
lock_key = 'lock:resource:document123'
lock_value = str(uuid.uuid4())  # Unique value per client
lock_ttl = 30  # 30 seconds

acquired = redis.set(
    lock_key,
    lock_value,
    nx=True,        # Only set if not exists
    ex=lock_ttl     # Expire after lock_ttl seconds
)

if acquired:
    try:
        # Critical section
        process_document()
    finally:
        # Release lock only if we still own it
        if redis.get(lock_key) == lock_value:
            redis.delete(lock_key)
```

**Why unique lock value?**
Prevents client A from releasing client B's lock if A's processing exceeded TTL.

#### Redis-py Lock Context Manager
```python
import redis
from redis.lock import Lock

r = redis.Redis(host='localhost', port=6379, db=0)

# Using context manager (recommended)
with r.lock('lock:resource:document123', timeout=30, blocking_timeout=5):
    # Critical section
    # Lock automatically released when exiting context
    process_document()

# Manual lock management
lock = r.lock('lock:resource:document123', timeout=30)
if lock.acquire(blocking=True, blocking_timeout=5):
    try:
        process_document()
    finally:
        lock.release()
```

**Parameters:**
- `timeout`: Lock expiration time (prevents deadlocks if client crashes)
- `blocking`: Whether to wait for lock
- `blocking_timeout`: Max time to wait for lock acquisition

#### Preventing Duplicate Ingestion Jobs

**Use case**: Ensure only one worker processes a given source at a time.

```python
def ingest_source(source_id: str):
    lock_key = f'lock:ingestion:{source_id}'
    lock = redis.lock(lock_key, timeout=600, blocking_timeout=1)

    if not lock.acquire(blocking=False):
        # Another worker is already processing this source
        logger.info(f'Source {source_id} already being processed')
        return

    try:
        # Perform ingestion
        documents = fetch_documents(source_id)
        for doc in documents:
            process_document(doc)
    finally:
        lock.release()
```

#### Distributed Lock with Refresh
For long-running operations, periodically extend lock:

```python
import threading

def keep_alive_lock(lock, stop_event, refresh_interval=10):
    """Background thread to refresh lock"""
    while not stop_event.is_set():
        try:
            lock.reacquire()
            time.sleep(refresh_interval)
        except:
            break

def long_running_ingestion(source_id):
    lock = redis.lock(f'lock:ingestion:{source_id}', timeout=60)
    if not lock.acquire(blocking=False):
        return

    stop_event = threading.Event()
    refresh_thread = threading.Thread(
        target=keep_alive_lock,
        args=(lock, stop_event, 30)
    )
    refresh_thread.start()

    try:
        # Long-running operation
        process_large_dataset()
    finally:
        stop_event.set()
        refresh_thread.join()
        lock.release()
```

### Redlock Algorithm (Multi-Redis Instances)

**For production systems with high availability requirements:**

```python
from redlock import Redlock

# Multiple Redis instances for fault tolerance
redlock = Redlock([
    {'host': 'redis1', 'port': 6379, 'db': 0},
    {'host': 'redis2', 'port': 6379, 'db': 0},
    {'host': 'redis3', 'port': 6379, 'db': 0},
])

lock = redlock.lock('lock:resource:document123', 30000)  # 30 second TTL
if lock:
    try:
        process_document()
    finally:
        redlock.unlock(lock)
```

**Redlock properties:**
- Acquires lock on majority of Redis instances (N/2 + 1)
- More resilient to single Redis instance failure
- Recommended for critical operations

**Sources:**
- https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- https://codedamn.com/news/backend/distributed-locks-with-redis
- https://medium.com/geekculture/distributed-lock-implementation-with-redis-and-python-22ae932e10ee
- https://pypi.org/project/python-redis-lock/
- https://github.com/glasslion/redlock

---

## Python Libraries and Implementation

### redis-py (Official Client)

**Installation:**
```bash
pip install redis
```

**Basic connection:**
```python
import redis

# Synchronous client
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Connection pool (recommended for multi-threaded apps)
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)

# From URL
r = redis.from_url('redis://localhost:6379/0')
```

**Sources:**
- https://redis-py.readthedocs.io/
- https://realpython.com/python-redis/

### Async Operations with redis-py

**Installation** (same package, built-in async support):
```bash
pip install redis>=4.2.0
```

**Basic async patterns:**
```python
import redis.asyncio as redis
import asyncio

async def main():
    # Create async connection
    r = await redis.from_url('redis://localhost:6379')

    # Basic operations
    await r.set('key', 'value')
    value = await r.get('key')

    # Close connection
    await r.close()

# Run async code
asyncio.run(main())
```

**Async pub/sub pattern:**
```python
async def reader(channel: redis.client.PubSub):
    async for message in channel.listen():
        if message['type'] == 'message':
            print(f"Received: {message['data']}")

async def main():
    r = await redis.from_url('redis://localhost:6379')

    async with r.pubsub() as pubsub:
        await pubsub.subscribe('channel:updates')

        # Create task for reading messages
        task = asyncio.create_task(reader(pubsub))

        # Publish messages
        await r.publish('channel:updates', 'Hello!')

        await task

asyncio.run(main())
```

**Async pipeline pattern:**
```python
async def bulk_operations():
    r = await redis.from_url('redis://localhost:6379')

    async with r.pipeline(transaction=True) as pipe:
        # Queue multiple operations
        pipe.set('key1', 'value1')
        pipe.set('key2', 'value2')
        pipe.get('key1')

        # Execute atomically
        results = await pipe.execute()

    await r.close()
```

**Best practices:**
- Use connection pooling
- Use `async with` context managers
- Avoid `time.sleep()`, use `await asyncio.sleep()` instead
- Use `asyncio.gather()` for concurrent operations

**Sources:**
- https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
- https://redis.io/blog/async-await-programming-basics-python-examples/
- https://proxiesapi.com/articles/unlocking-async-performance-with-asyncio-redis

### Specialized Libraries

#### python-redis-lock
```bash
pip install python-redis-lock
```

```python
import redis_lock

with redis_lock.Lock(redis_client, 'resource_name'):
    # Critical section
    pass
```

#### redlock-py
```bash
pip install redlock-py
```

For distributed locks across multiple Redis instances (Redlock algorithm).

#### redis-om-python
```bash
pip install redis-om
```

Object mapping for Redis with Pydantic models (similar to ORM).

---

## Code Examples

### Complete Deduplication System

```python
import hashlib
import json
from typing import Optional, Set
from datetime import datetime
import redis

class DocumentDeduplicator:
    """
    Redis-backed deduplication system for RAG pipelines.

    Features:
    - Content-based hashing with normalization
    - Redis Sets for exact deduplication
    - Metadata storage with hashes
    - TTL support for temporary deduplication
    """

    def __init__(self, redis_client: redis.Redis, namespace: str = 'dedup'):
        self.redis = redis_client
        self.namespace = namespace

    def normalize_content(self, content: str) -> str:
        """Normalize content before hashing."""
        # Convert to lowercase
        content = content.lower()

        # Remove extra whitespace
        content = ' '.join(content.split())

        # Remove common punctuation (optional)
        # content = re.sub(r'[^\w\s]', '', content)

        return content

    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of normalized content."""
        normalized = self.normalize_content(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def is_duplicate(self, content: str, source: Optional[str] = None) -> bool:
        """
        Check if content has been seen before.

        Args:
            content: Document content to check
            source: Optional source identifier (e.g., 'gmail', 'github')

        Returns:
            True if content is a duplicate, False otherwise
        """
        content_hash = self.compute_hash(content)

        if source:
            key = f'{self.namespace}:hash:{source}'
        else:
            key = f'{self.namespace}:hash:all'

        return bool(self.redis.sismember(key, content_hash))

    def mark_seen(
        self,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
        ttl: Optional[int] = None
    ) -> str:
        """
        Mark content as seen and store metadata.

        Args:
            content: Document content
            source: Optional source identifier
            metadata: Optional metadata to store
            ttl: Optional time-to-live in seconds

        Returns:
            Content hash
        """
        content_hash = self.compute_hash(content)

        # Add to hash set
        if source:
            hash_key = f'{self.namespace}:hash:{source}'
        else:
            hash_key = f'{self.namespace}:hash:all'

        self.redis.sadd(hash_key, content_hash)

        # Store metadata if provided
        if metadata:
            meta_key = f'{self.namespace}:meta:{content_hash}'
            metadata_with_timestamp = {
                **metadata,
                'first_seen': datetime.now().isoformat(),
                'hash': content_hash,
                'source': source or 'unknown'
            }
            self.redis.hset(meta_key, mapping=metadata_with_timestamp)

            if ttl:
                self.redis.expire(meta_key, ttl)

        return content_hash

    def add_if_new(
        self,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> tuple[bool, str]:
        """
        Add content if not already seen.

        Args:
            content: Document content
            source: Optional source identifier
            metadata: Optional metadata

        Returns:
            Tuple of (is_new, content_hash)
        """
        if self.is_duplicate(content, source):
            content_hash = self.compute_hash(content)
            return False, content_hash

        content_hash = self.mark_seen(content, source, metadata)
        return True, content_hash

    def get_metadata(self, content_hash: str) -> Optional[dict]:
        """Retrieve metadata for a content hash."""
        meta_key = f'{self.namespace}:meta:{content_hash}'
        metadata = self.redis.hgetall(meta_key)
        return metadata if metadata else None

    def get_stats(self, source: Optional[str] = None) -> dict:
        """Get deduplication statistics."""
        if source:
            hash_key = f'{self.namespace}:hash:{source}'
        else:
            hash_key = f'{self.namespace}:hash:all'

        count = self.redis.scard(hash_key)
        return {
            'source': source or 'all',
            'unique_documents': count
        }


# Usage example
def main():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Create deduplicator
    dedup = DocumentDeduplicator(r, namespace='rag')

    # Example documents
    doc1 = "The quick brown fox jumps over the lazy dog."
    doc2 = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG."  # Same content, different case
    doc3 = "A completely different document."

    # Check and add documents
    is_new, hash1 = dedup.add_if_new(
        doc1,
        source='gmail',
        metadata={'doc_id': 'msg_001', 'subject': 'Test Email'}
    )
    print(f"Doc1 is new: {is_new}, hash: {hash1}")

    is_new, hash2 = dedup.add_if_new(doc2, source='gmail')
    print(f"Doc2 is new: {is_new}, hash: {hash2}")  # Should be duplicate

    is_new, hash3 = dedup.add_if_new(doc3, source='slack')
    print(f"Doc3 is new: {is_new}, hash: {hash3}")

    # Get statistics
    print(dedup.get_stats('gmail'))
    print(dedup.get_stats('slack'))
    print(dedup.get_stats())

if __name__ == '__main__':
    main()
```

### Incremental Sync Manager

```python
import json
from datetime import datetime
from typing import Optional, Dict, Any
import redis

class SyncStateManager:
    """
    Manages incremental sync state for multiple sources.

    Features:
    - Cursor and timestamp tracking
    - Source-specific state management
    - Failure recovery
    - Sync scheduling
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def get_cursor(self, source: str, identifier: str) -> Optional[str]:
        """
        Get cursor for incremental sync.

        Args:
            source: Source type (e.g., 'gmail', 'github')
            identifier: Source-specific identifier (e.g., user ID, repo name)

        Returns:
            Cursor value or None if no previous sync
        """
        key = f'cursor:{source}:{identifier}'
        return self.redis.get(key)

    def set_cursor(
        self,
        source: str,
        identifier: str,
        cursor: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update cursor after successful sync."""
        # Store cursor
        key = f'cursor:{source}:{identifier}'
        self.redis.set(key, cursor)

        # Store metadata
        if metadata is None:
            metadata = {}

        metadata_with_timestamp = {
            **metadata,
            'cursor': cursor,
            'last_sync': datetime.now().isoformat(),
            'status': 'success'
        }

        meta_key = f'cursor:state:{source}:{identifier}'
        self.redis.hset(meta_key, mapping=metadata_with_timestamp)

        # Update sync schedule (for priority tracking)
        schedule_key = 'sync:schedule:all'
        self.redis.zadd(schedule_key, {
            f'{source}:{identifier}': datetime.now().timestamp()
        })

    def get_state(self, source: str, identifier: str) -> Dict[str, Any]:
        """Get full sync state including metadata."""
        meta_key = f'cursor:state:{source}:{identifier}'
        state = self.redis.hgetall(meta_key)
        return state if state else {}

    def mark_sync_failed(
        self,
        source: str,
        identifier: str,
        error: str
    ):
        """Mark sync as failed for monitoring."""
        meta_key = f'cursor:state:{source}:{identifier}'
        self.redis.hset(meta_key, mapping={
            'last_error': error,
            'last_error_time': datetime.now().isoformat(),
            'status': 'failed'
        })

    def get_sources_to_sync(
        self,
        max_age_seconds: int = 3600,
        limit: int = 10
    ) -> list[str]:
        """
        Get sources that need syncing based on last sync time.

        Args:
            max_age_seconds: Maximum age before source needs re-sync
            limit: Maximum number of sources to return

        Returns:
            List of source identifiers (format: 'source:identifier')
        """
        schedule_key = 'sync:schedule:all'
        cutoff = datetime.now().timestamp() - max_age_seconds

        # Get sources not synced since cutoff
        stale_sources = self.redis.zrangebyscore(
            schedule_key,
            '-inf',
            cutoff,
            start=0,
            num=limit
        )

        return [s.decode() if isinstance(s, bytes) else s for s in stale_sources]


# Gmail-specific sync implementation
class GmailSyncManager:
    """Gmail-specific incremental sync using historyId."""

    def __init__(self, redis_client: redis.Redis, gmail_service):
        self.state_manager = SyncStateManager(redis_client)
        self.gmail = gmail_service

    def full_sync(self, user_id: str):
        """Perform full sync and store historyId."""
        # Fetch messages
        response = self.gmail.users().messages().list(
            userId=user_id,
            maxResults=100
        ).execute()

        messages = response.get('messages', [])

        if messages:
            # Get historyId from latest message
            latest_msg = self.gmail.users().messages().get(
                userId=user_id,
                id=messages[0]['id']
            ).execute()

            history_id = latest_msg.get('historyId')

            # Store cursor
            self.state_manager.set_cursor(
                'gmail',
                user_id,
                history_id,
                metadata={'message_count': len(messages)}
            )

        return messages

    def incremental_sync(self, user_id: str):
        """Perform incremental sync using historyId."""
        # Get stored historyId
        history_id = self.state_manager.get_cursor('gmail', user_id)

        if not history_id:
            # No cursor, perform full sync
            return self.full_sync(user_id)

        try:
            # Fetch history
            response = self.gmail.users().history().list(
                userId=user_id,
                startHistoryId=history_id
            ).execute()

            changes = response.get('history', [])

            # Process changes
            for record in changes:
                # Handle messagesAdded, messagesDeleted, etc.
                if 'messagesAdded' in record:
                    for msg_data in record['messagesAdded']:
                        process_message(msg_data['message'])

            # Update cursor to new historyId
            new_history_id = response.get('historyId', history_id)
            self.state_manager.set_cursor(
                'gmail',
                user_id,
                new_history_id,
                metadata={'changes_processed': len(changes)}
            )

            return changes

        except Exception as e:
            self.state_manager.mark_sync_failed('gmail', user_id, str(e))
            raise


# GitHub-specific sync implementation
class GitHubSyncManager:
    """GitHub-specific incremental sync using 'since' parameter."""

    def __init__(self, redis_client: redis.Redis, github_api):
        self.state_manager = SyncStateManager(redis_client)
        self.github = github_api

    def incremental_sync(self, owner: str, repo: str):
        """Sync GitHub issues updated since last sync."""
        identifier = f'{owner}/{repo}'

        # Get last sync timestamp
        state = self.state_manager.get_state('github', identifier)
        last_sync = state.get('last_sync', '1970-01-01T00:00:00Z')

        params = {
            'since': last_sync,
            'state': 'all',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100
        }

        all_issues = []
        page = 1

        while True:
            params['page'] = page
            response = self.github.get(
                f'/repos/{owner}/{repo}/issues',
                params=params
            )
            issues = response.json()

            if not issues:
                break

            # Process issues
            for issue in issues:
                # Stop if we've seen this before (optimization)
                if issue['updated_at'] <= last_sync:
                    break

                all_issues.append(issue)

            page += 1

        # Update sync state
        if all_issues:
            self.state_manager.set_cursor(
                'github',
                identifier,
                datetime.now().isoformat(),
                metadata={
                    'issues_synced': len(all_issues),
                    'latest_issue': all_issues[0]['updated_at']
                }
            )

        return all_issues


# Helper function
def process_message(message):
    """Placeholder for message processing logic."""
    print(f"Processing message: {message.get('id')}")
```

### Dead Letter Queue with Retry Logic

```python
import json
import time
import traceback
from typing import Any, Callable, Optional
from datetime import datetime
from enum import Enum
import redis

class ErrorType(Enum):
    TRANSIENT = 'transient'
    PERMANENT = 'permanent'

class DeadLetterQueue:
    """
    Redis-backed Dead Letter Queue with retry logic.

    Features:
    - Automatic retry with exponential backoff
    - Error classification (transient vs permanent)
    - TTL-based message expiration
    - Parking lot for permanent failures
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_attempts: int = 5,
        base_backoff: int = 2
    ):
        self.redis = redis_client
        self.max_attempts = max_attempts
        self.base_backoff = base_backoff

    def send_to_dlq(
        self,
        message: dict,
        error: Exception,
        error_type: ErrorType = ErrorType.TRANSIENT,
        source: str = 'unknown'
    ):
        """Send failed message to DLQ."""
        attempts = message.get('attempts', 0) + 1

        dlq_message = {
            'id': message.get('id', str(time.time())),
            'original_message': message,
            'error': str(error),
            'error_type': error_type.value,
            'stack_trace': traceback.format_exc(),
            'attempts': attempts,
            'first_failed_at': message.get('first_failed_at', datetime.now().isoformat()),
            'last_failed_at': datetime.now().isoformat(),
            'source': source
        }

        if error_type == ErrorType.PERMANENT or attempts >= self.max_attempts:
            # Move to parking lot (permanent failures)
            self.redis.lpush(
                'dlq:parking',
                json.dumps(dlq_message)
            )
        else:
            # Schedule for retry with backoff
            backoff_seconds = self.base_backoff ** attempts
            retry_time = time.time() + backoff_seconds

            self.redis.zadd(
                'dlq:scheduled_retries',
                {json.dumps(dlq_message): retry_time}
            )

    def process_retries(self, processor: Callable[[dict], Any]) -> int:
        """
        Process messages scheduled for retry.

        Args:
            processor: Function to process message

        Returns:
            Number of messages processed
        """
        now = time.time()

        # Get messages ready for retry
        ready_messages = self.redis.zrangebyscore(
            'dlq:scheduled_retries',
            '-inf',
            now,
            start=0,
            num=10
        )

        processed = 0

        for message_json in ready_messages:
            if isinstance(message_json, bytes):
                message_json = message_json.decode('utf-8')

            dlq_message = json.loads(message_json)
            original_message = dlq_message['original_message']

            try:
                # Process message
                processor(original_message)

                # Success: Remove from retry queue
                self.redis.zrem('dlq:scheduled_retries', message_json)
                processed += 1

            except Exception as e:
                # Failed again: Update and reschedule
                error_type = self.classify_error(e)

                # Remove old entry
                self.redis.zrem('dlq:scheduled_retries', message_json)

                # Re-add with updated attempts
                self.send_to_dlq(
                    original_message,
                    e,
                    error_type,
                    dlq_message['source']
                )

        return processed

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error as transient or permanent."""
        # Permanent errors (poison pills)
        if isinstance(error, (ValueError, KeyError, TypeError)):
            return ErrorType.PERMANENT

        # Transient errors (worth retrying)
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorType.TRANSIENT

        # Default to transient for safety
        return ErrorType.TRANSIENT

    def get_parking_lot_messages(self, limit: int = 10) -> list[dict]:
        """Retrieve messages from parking lot for manual review."""
        messages_json = self.redis.lrange('dlq:parking', 0, limit - 1)
        return [json.loads(m) for m in messages_json]

    def reprocess_parking_lot_message(
        self,
        message_index: int,
        processor: Callable[[dict], Any]
    ) -> bool:
        """
        Manually reprocess a message from parking lot.

        Args:
            message_index: Index in parking lot
            processor: Function to process message

        Returns:
            True if successful, False otherwise
        """
        # Get message
        message_json = self.redis.lindex('dlq:parking', message_index)
        if not message_json:
            return False

        dlq_message = json.loads(message_json)
        original_message = dlq_message['original_message']

        try:
            # Process message
            processor(original_message)

            # Success: Remove from parking lot
            self.redis.lrem('dlq:parking', 1, message_json)
            return True

        except Exception as e:
            # Still failing: Keep in parking lot, update error
            dlq_message['last_manual_retry'] = datetime.now().isoformat()
            dlq_message['last_error'] = str(e)

            # Update in place
            self.redis.lset('dlq:parking', message_index, json.dumps(dlq_message))
            return False

    def get_stats(self) -> dict:
        """Get DLQ statistics."""
        return {
            'scheduled_retries': self.redis.zcard('dlq:scheduled_retries'),
            'parking_lot': self.redis.llen('dlq:parking'),
            'next_retry_at': self._get_next_retry_time()
        }

    def _get_next_retry_time(self) -> Optional[str]:
        """Get timestamp of next scheduled retry."""
        next_retry = self.redis.zrange(
            'dlq:scheduled_retries',
            0,
            0,
            withscores=True
        )

        if next_retry:
            _, timestamp = next_retry[0]
            return datetime.fromtimestamp(timestamp).isoformat()

        return None


# Usage example
def main():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    dlq = DeadLetterQueue(r, max_attempts=3)

    def process_document(message: dict):
        """Example processor that might fail."""
        doc_id = message['doc_id']

        # Simulate processing that might fail
        if doc_id == 'bad_doc':
            raise ValueError("Invalid document format")

        print(f"Successfully processed: {doc_id}")

    # Example: Send message to DLQ
    try:
        process_document({'doc_id': 'bad_doc'})
    except Exception as e:
        dlq.send_to_dlq(
            {'doc_id': 'bad_doc', 'content': 'test'},
            e,
            ErrorType.PERMANENT,
            source='gmail'
        )

    # Process retries periodically
    while True:
        processed = dlq.process_retries(process_document)
        print(f"Processed {processed} retry messages")

        # Check stats
        stats = dlq.get_stats()
        print(f"DLQ Stats: {stats}")

        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    main()
```

### Distributed Lock for Concurrent Processing

```python
import time
import uuid
from typing import Callable, Any, Optional
from contextlib import contextmanager
import redis

class DistributedLock:
    """
    Distributed lock implementation with Redis.

    Features:
    - Automatic expiration (prevents deadlocks)
    - Unique lock values (prevents accidental release)
    - Context manager support
    - Lock refresh for long operations
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        lock_key: str,
        ttl: int = 30,
        blocking_timeout: Optional[int] = None
    ):
        self.redis = redis_client
        self.lock_key = f'lock:{lock_key}'
        self.ttl = ttl
        self.blocking_timeout = blocking_timeout
        self.lock_value = str(uuid.uuid4())
        self.acquired = False

    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: Whether to wait for lock if not available

        Returns:
            True if lock acquired, False otherwise
        """
        if blocking and self.blocking_timeout:
            # Try to acquire with timeout
            end_time = time.time() + self.blocking_timeout

            while time.time() < end_time:
                if self._try_acquire():
                    return True
                time.sleep(0.1)

            return False

        elif blocking:
            # Block indefinitely
            while not self._try_acquire():
                time.sleep(0.1)
            return True

        else:
            # Non-blocking
            return self._try_acquire()

    def _try_acquire(self) -> bool:
        """Attempt to acquire lock once."""
        acquired = self.redis.set(
            self.lock_key,
            self.lock_value,
            nx=True,
            ex=self.ttl
        )

        if acquired:
            self.acquired = True

        return bool(acquired)

    def release(self):
        """Release the lock if we own it."""
        if not self.acquired:
            return

        # Only release if we still own the lock
        # Use Lua script for atomicity
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        self.redis.eval(lua_script, 1, self.lock_key, self.lock_value)
        self.acquired = False

    def extend(self, additional_time: Optional[int] = None):
        """Extend lock TTL."""
        if not self.acquired:
            return False

        ttl = additional_time or self.ttl

        # Only extend if we still own the lock
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = self.redis.eval(
            lua_script,
            1,
            self.lock_key,
            self.lock_value,
            ttl
        )

        return bool(result)

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


@contextmanager
def distributed_lock(
    redis_client: redis.Redis,
    resource_name: str,
    ttl: int = 30,
    blocking_timeout: Optional[int] = 5
):
    """
    Convenience context manager for distributed locks.

    Usage:
        with distributed_lock(redis, 'resource:123'):
            # Critical section
            pass
    """
    lock = DistributedLock(redis_client, resource_name, ttl, blocking_timeout)

    if not lock.acquire(blocking=True):
        raise TimeoutError(f'Could not acquire lock for {resource_name}')

    try:
        yield lock
    finally:
        lock.release()


# Usage example: Prevent duplicate ingestion
def ingest_source_safely(
    redis_client: redis.Redis,
    source_id: str,
    fetch_func: Callable[[], list]
):
    """
    Ingest from source with distributed locking to prevent duplicates.

    Args:
        redis_client: Redis client
        source_id: Unique source identifier
        fetch_func: Function to fetch documents from source
    """
    lock_key = f'ingestion:{source_id}'

    # Try to acquire lock (non-blocking)
    lock = DistributedLock(redis_client, lock_key, ttl=600, blocking_timeout=1)

    if not lock.acquire(blocking=False):
        print(f'Source {source_id} is already being processed')
        return

    try:
        # Perform ingestion
        documents = fetch_func()

        for doc in documents:
            # Process each document
            process_document(doc)

        print(f'Successfully ingested {len(documents)} documents from {source_id}')

    finally:
        lock.release()


# Usage example: Long-running operation with lock refresh
def long_running_ingestion(
    redis_client: redis.Redis,
    source_id: str
):
    """Example of long-running operation with periodic lock refresh."""
    lock_key = f'ingestion:{source_id}'

    with distributed_lock(redis_client, lock_key, ttl=60) as lock:
        # Simulate long operation
        for i in range(10):
            # Do some work
            time.sleep(10)

            # Refresh lock every iteration
            lock.extend()
            print(f'Extended lock for {source_id}')


# Helper function
def process_document(doc):
    """Placeholder for document processing."""
    print(f"Processing document: {doc.get('id')}")


# Main example
def main():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Example 1: Prevent duplicate processing
    def fetch_documents():
        return [
            {'id': 'doc1', 'content': 'test1'},
            {'id': 'doc2', 'content': 'test2'}
        ]

    ingest_source_safely(r, 'gmail:user123', fetch_documents)

    # Example 2: Using context manager directly
    with distributed_lock(r, 'critical:resource', ttl=30):
        # Critical section
        print("Performing critical operation")
        time.sleep(5)

if __name__ == '__main__':
    main()
```

---

## Summary and Recommendations

### Deduplication Strategy
1. **Use SHA-256 hashing** for content-based deduplication with proper normalization
2. **Implement fuzzy deduplication** with MinHash/LSH for near-duplicate detection
3. **Choose appropriate Redis structure**:
   - Sets for exact deduplication (small-medium datasets)
   - Bloom filters for probabilistic deduplication (large datasets, 92%+ memory savings)
   - Hashes for storing metadata with content hashes

### State Management
1. **Use hierarchical key naming** with colon delimiters (`source:id:field`)
2. **Store cursors and timestamps** for incremental sync
3. **Implement source-specific patterns**:
   - Gmail: historyId with push notifications
   - GitHub: `since` parameter with timestamp tracking
   - Generic: hybrid cursor + timestamp approach

### Dead Letter Queue
1. **Use Redis Lists** for simple FIFO queue operations
2. **Use Redis Streams** for advanced features (consumer groups, delivery tracking)
3. **Implement retry logic** with exponential backoff
4. **Classify errors** (transient vs permanent) to avoid infinite loops
5. **Use parking lot** for permanent failures requiring manual review

### Concurrency Control
1. **Use distributed locks** to prevent duplicate processing
2. **Implement lock refresh** for long-running operations
3. **Use unique lock values** to prevent accidental release
4. **Set appropriate TTL** to prevent deadlocks
5. **Consider Redlock** for high-availability requirements (multiple Redis instances)

### Python Implementation
1. **Use redis-py 4.2+** with built-in async support
2. **Use connection pooling** for multi-threaded applications
3. **Use async patterns** (asyncio) for I/O-bound operations
4. **Use context managers** for automatic resource cleanup
5. **Implement proper error handling** and logging

---

## References

### Documentation
- https://redis.io/docs/latest/develop/
- https://redis-py.readthedocs.io/
- https://developers.google.com/gmail/api/guides/sync
- https://docs.github.com/rest/guides/using-pagination-in-the-rest-api

### Articles and Tutorials
- https://redis.io/solutions/deduplication/
- https://dev.to/rijultp/redis-naming-conventions-every-developer-should-know-1ip
- https://medium.com/nerd-for-tech/unveiling-the-art-of-redis-key-naming-best-practices-6e20f3839e4a
- https://codedamn.com/news/backend/distributed-locks-with-redis
- https://dev.to/faranmustafa/implementing-a-reliable-event-driven-system-with-dead-letter-queues-in-golang-and-redis-43pb
- https://levelup.gitconnected.com/harnessing-python-and-sha-256-an-intuitive-guide-to-removing-duplicate-files-d3b02e0b3978
- https://www.narrative.io/knowledge-base/how-to-guides/how-to-normalize-emails-prior-to-hashing
- https://medium.com/@tahir.saeed_46137/chunking-and-embedding-strategies-in-rag-a-guide-to-optimizing-retrieval-augmented-generation-7c95432423b1

### RAG Pipeline Resources
- https://redis.io/docs/latest/develop/get-started/rag/
- https://www.weblineindia.com/blog/build-rag-with-langchain-redis-vector-search/
- https://learn.microsoft.com/en-us/azure/databricks/generative-ai/tutorials/ai-cookbook/quality-data-pipeline-rag
- https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089

### Python Libraries
- https://pypi.org/project/python-redis-lock/
- https://github.com/glasslion/redlock
- https://github.com/ChenghaoMou/text-dedup
- https://github.com/MinishLab/semhash

---

**Document Version:** 1.0
**Last Updated:** 2024-09-30
**Author:** Research compiled from web sources and best practices
