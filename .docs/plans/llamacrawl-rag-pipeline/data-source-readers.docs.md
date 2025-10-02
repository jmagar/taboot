# LlamaIndex Data Source Readers - Research Documentation

This document provides comprehensive research findings on LlamaIndex data source readers for the 5 initial sources: Firecrawl, GitHub, Reddit, Elasticsearch, and Gmail.

## Table of Contents

1. [FireCrawlWebReader](#firecrawlwebreader)
2. [GitHubRepositoryReader](#githubrepositoryreader)
3. [RedditReader](#redditreader)
4. [ElasticsearchReader](#elasticsearchreader)
5. [GmailReader](#gmailreader)
6. [Common Patterns](#common-patterns)
7. [References](#references)

---

## FireCrawlWebReader

### Overview

FireCrawlWebReader is a LlamaIndex integration for Firecrawl, a web data API for AI that turns websites into LLM-ready markdown or structured data. Currently, the LlamaIndex integration uses Firecrawl API v0, though Firecrawl has released v2 with enhanced features.

**Key Resources:**
- LlamaIndex Integration: https://docs.firecrawl.dev/integrations/llamaindex
- Firecrawl Python SDK: https://docs.firecrawl.dev/sdks/python
- GitHub Repository: https://github.com/firecrawl/firecrawl

### Firecrawl v2 API Modes

Firecrawl v2 offers four primary endpoints for web data extraction:

#### 1. Scrape Mode (`/scrape`)
- Used to scrape a single URL and get its content in specified formats
- Supports multiple output formats: markdown, html, structured data
- Ideal for extracting data from single web pages

#### 2. Crawl Mode (`/crawl`)
- Crawls a URL and all accessible subpages
- Submits a crawl job and returns a job ID to check status
- Supports natural language prompts for crawling in v2
- Automatically handles pagination and navigation

#### 3. Map Mode (`/map`)
- Generates a list of URLs from a website
- Extremely fast for URL discovery
- Options to search for specific URLs inside a website
- Can exclude subdomains or utilize sitemap

#### 4. Extract Mode (`/extract`)
- AI-powered structured data extraction
- Extract from single pages, multiple pages, or entire websites
- Uses natural language prompts to define extraction schema
- Returns LLM-ready structured data

### Configuration Options

**Installation:**
```bash
pip install llama-index-readers-web
# Or for Firecrawl v2 SDK directly
pip install firecrawl-py
```

**Basic LlamaIndex Configuration:**
```python
from llama_index.readers.web import FireCrawlWebReader

firecrawl_reader = FireCrawlWebReader(
    api_key="<your_api_key>",  # Get from https://www.firecrawl.dev/
    mode="scrape",  # Choose between "crawl" and "scrape"
    params={"additional": "parameters"}  # Optional additional parameters
)
```

**Firecrawl v2 SDK Configuration:**
```python
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-YOUR_API_KEY")
```

### Code Examples

#### Example 1: Basic Scraping with LlamaIndex
```python
from llama_index.readers.web import FireCrawlWebReader
from llama_index.core import SummaryIndex
import os

# Initialize FireCrawlWebReader
firecrawl_reader = FireCrawlWebReader(
    api_key="<your_api_key>",
    mode="scrape",
    params={"additional": "parameters"}
)

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "<OPENAI_API_KEY>"

# Load documents from a URL
documents = firecrawl_reader.load_data(url="http://paulgraham.com/")

# Create an index from the documents
index = SummaryIndex.from_documents(documents)

# Create a query engine and query the data
query_engine = index.as_query_engine()
response = query_engine.query("What did the author do growing up?")
print(response)
```

#### Example 2: Using Firecrawl v2 SDK Directly (Scrape)
```python
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-YOUR_API_KEY")

# Scrape a website with multiple formats
scrape_status = firecrawl.scrape(
    'https://firecrawl.dev',
    formats=['markdown', 'html']
)
print(scrape_status)
```

#### Example 3: Crawling with Firecrawl v2 SDK
```python
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-YOUR_API_KEY")

# Crawl a website with limit and format options
crawl_status = firecrawl.crawl(
    'https://firecrawl.dev',
    limit=100,
    scrape_options={
        'formats': ['markdown', 'html']
    }
)
print(crawl_status)
```

#### Example 4: Async Operations with Firecrawl v2
```python
import asyncio
from firecrawl import AsyncFirecrawl

async def main():
    firecrawl = AsyncFirecrawl(api_key="fc-YOUR-API-KEY")

    # Scrape
    doc = await firecrawl.scrape("https://firecrawl.dev", formats=["markdown"])
    print(doc.get("markdown"))

    # Crawl (start + status)
    started = await firecrawl.start_crawl("https://docs.firecrawl.dev", limit=3)
    status = await firecrawl.get_crawl_status(started.id)
    print(status.status)

    # Batch scrape
    job = await firecrawl.batch_scrape([
        "https://firecrawl.dev",
        "https://docs.firecrawl.dev",
    ], formats=["markdown"], poll_interval=1, timeout=60)
    print(job.status, job.completed, job.total)

asyncio.run(main())
```

### Integration Status

- LlamaIndex integration currently uses Firecrawl v0 API
- Firecrawl v2 SDK can be used directly alongside LlamaIndex
- Active development to update LangChain and LlamaIndex integrations for v2 compatibility
- Consider using Firecrawl v2 SDK directly for new features (map, extract modes)

---

## GitHubRepositoryReader

### Overview

GitHubRepositoryReader retrieves the contents of a GitHub repository and returns a list of documents. It can load repository files, issues, and pull requests with filtering capabilities.

**Key Resources:**
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/github/
- PyPI Package: https://pypi.org/project/llama-index-readers-github/
- Use Case Example: https://docs.llamaindex.ai/en/stable/examples/usecases/github_issue_analysis/

### Loading Repos, Issues, and PRs

LlamaIndex provides separate readers for different GitHub data types:

#### 1. GithubRepositoryReader
- Loads repository files and content
- Supports file filtering by extension, directory, and path
- Can use custom parsers for file processing

#### 2. GitHubRepositoryIssuesReader
- Retrieves list of issues from a repository
- Returns documents with issue content and metadata

#### 3. GitHubPRReader
- Loads pull request data
- Includes PR content and metadata

### Configuration Options

**Installation:**
```bash
pip install llama-index-readers-github
```

**Requirements:**
- Python 3.9 or higher
- GitHub personal access token

**Key Parameters:**
- `github_client`: GithubClient instance with authentication token
- `owner`: Repository owner username or organization
- `repo`: Repository name
- `use_parser`: Whether to use file parser (default: False)
- `verbose`: Enable verbose logging
- `filter_directories`: Tuple of (directories, FilterType)
- `filter_file_extensions`: Tuple of (extensions, FilterType)

### Incremental Sync Patterns

**Current Status:**
- LlamaIndex GitHubRepositoryReader does not have built-in incremental sync
- Manual implementation required for tracking changes

**Recommended Approach:**
```python
# 1. Track last sync timestamp
last_sync_time = load_last_sync_timestamp()

# 2. Use GitHub API to filter by date
# Note: This requires direct API calls, not built into reader
since = datetime.fromisoformat(last_sync_time)

# 3. Load only new/updated content
# Implement custom logic to filter documents by modification date

# 4. Save new sync timestamp
save_last_sync_timestamp(datetime.now().isoformat())
```

**Alternative Pattern:**
Use LlamaIndex's IngestionPipeline with document management to automatically detect and update changed documents based on content hashes.

### Code Examples

#### Example 1: Basic Repository Loading
```python
from llama_index.readers.github import GithubRepositoryReader, GithubClient
import os

# Initialize GitHub client
github_token = os.environ.get("GITHUB_TOKEN")
github_client = GithubClient(github_token=github_token, verbose=False)

# Initialize reader
reader = GithubRepositoryReader(
    github_client=github_client,
    owner="run-llama",
    repo="llama_index",
    use_parser=False,
    verbose=True,
    filter_directories=(
        ["docs"],
        GithubRepositoryReader.FilterType.INCLUDE,
    ),
    filter_file_extensions=(
        [".png", ".jpg", ".jpeg", ".gif", ".svg"],
        GithubRepositoryReader.FilterType.EXCLUDE,
    )
)

# Load documents from a specific branch
branch = "main"
documents = reader.load_data(branch=branch)
```

#### Example 2: Loading with File Filtering
```python
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core import VectorStoreIndex
import os

github_token = os.environ.get("GITHUB_TOKEN")
github_client = GithubClient(github_token=github_token, verbose=False)

# Load only Python and Markdown files from specific directories
documents = GithubRepositoryReader(
    github_client=github_client,
    owner="jerryjliu",
    repo="llama_index",
    use_parser=False,
    verbose=False,
    filter_directories=(
        ["examples", "tests"],
        GithubRepositoryReader.FilterType.EXCLUDE,
    ),
    filter_file_extensions=(
        [".py", ".md"],
        GithubRepositoryReader.FilterType.INCLUDE,
    )
).load_data(branch="main")

# Create index
index = VectorStoreIndex.from_documents(documents)
```

#### Example 3: Loading Issues
```python
from llama_index.readers.github import GitHubRepositoryIssuesReader, GithubClient

github_token = os.environ.get("GITHUB_TOKEN")
github_client = GithubClient(github_token=github_token)

# Initialize issues reader
issues_reader = GitHubRepositoryIssuesReader(
    github_client=github_client,
    owner="run-llama",
    repo="llama_index"
)

# Load issues
issues_documents = issues_reader.load_data()
```

#### Example 4: Using with Ingestion Pipeline for Incremental Updates
```python
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.readers.github import GithubRepositoryReader, GithubClient

# Initialize components
github_client = GithubClient(github_token=os.environ.get("GITHUB_TOKEN"))
reader = GithubRepositoryReader(
    github_client=github_client,
    owner="run-llama",
    repo="llama_index"
)

# Create pipeline with document store for tracking
docstore = SimpleDocumentStore()
pipeline = IngestionPipeline(
    transformations=[],
    docstore=docstore
)

# First run - loads all documents
documents = reader.load_data(branch="main")
nodes = pipeline.run(documents=documents)

# Subsequent runs - only processes changed documents
documents = reader.load_data(branch="main")
nodes = pipeline.run(documents=documents)  # Only new/changed docs processed
```

---

## RedditReader

### Overview

RedditReader is a subreddit post and top-level comments reader that loads text from relevant posts and comments using Reddit's API through PRAW (Python Reddit API Wrapper).

**Key Resources:**
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/reddit/
- PyPI Package: https://pypi.org/project/llama-index-readers-reddit/
- LlamaHub: https://llamahub.ai/l/readers/llama-index-readers-reddit

### PRAW Integration

RedditReader uses PRAW under the hood to connect to Reddit's API.

**Setup Requirements:**
1. Create a Reddit app at: https://www.reddit.com/prefs/apps
2. Scroll to bottom, click "create another app"
3. Select "script" as application type
4. Fill in details and click "create app"
5. Store credentials as environment variables:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
   - `REDDIT_USERNAME`
   - `REDDIT_PASSWORD`

### Subreddit Loading

**Key Parameters:**
- `subreddits`: List of subreddit names to search
- `search_keys`: List of keywords to search for in posts
- `post_limit`: Maximum number of posts to retrieve

### Pagination

RedditReader handles pagination internally through PRAW. The `post_limit` parameter controls how many posts are retrieved per subreddit.

### Configuration Options

**Installation:**
```bash
pip install llama-index-readers-reddit
```

### Code Examples

#### Example 1: Basic Reddit Loading
```python
from llama_index.core import VectorStoreIndex
from llama_index.readers.reddit import RedditReader

# Define parameters
subreddits = ["MachineLearning"]
search_keys = ["PyTorch", "deploy"]
post_limit = 10

# Initialize the RedditReader
loader = RedditReader()

# Load data from Reddit
documents = loader.load_data(
    subreddits=subreddits,
    search_keys=search_keys,
    post_limit=post_limit
)

# Create index and query
index = VectorStoreIndex.from_documents(documents)
response = index.query("What are the pain points of PyTorch users?")
print(response)
```

#### Example 2: Multiple Subreddits with Different Topics
```python
from llama_index.readers.reddit import RedditReader
import os

# Set Reddit credentials
os.environ["REDDIT_CLIENT_ID"] = "your_client_id"
os.environ["REDDIT_CLIENT_SECRET"] = "your_client_secret"
os.environ["REDDIT_USER_AGENT"] = "your_user_agent"
os.environ["REDDIT_USERNAME"] = "your_username"
os.environ["REDDIT_PASSWORD"] = "your_password"

# Initialize reader
reader = RedditReader()

# Load from multiple subreddits
subreddits = ["MachineLearning", "learnmachinelearning", "deeplearning"]
search_keys = ["LlamaIndex", "RAG", "retrieval"]
post_limit = 20

documents = reader.load_data(
    subreddits=subreddits,
    search_keys=search_keys,
    post_limit=post_limit
)

print(f"Loaded {len(documents)} documents from Reddit")
```

#### Example 3: Using with Ingestion Pipeline
```python
from llama_index.readers.reddit import RedditReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

# Initialize reader
reader = RedditReader()

# Load data
documents = reader.load_data(
    subreddits=["programming", "Python"],
    search_keys=["best practices", "design patterns"],
    post_limit=15
)

# Create ingestion pipeline
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512, chunk_overlap=50)
    ]
)

# Process documents
nodes = pipeline.run(documents=documents)
```

---

## ElasticsearchReader

### Overview

ElasticsearchReader reads documents from an Elasticsearch or OpenSearch index. These documents can be used in downstream LlamaIndex data structures with support for full Elasticsearch Query DSL.

**Key Resources:**
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/elasticsearch/
- PyPI Package: https://pypi.org/project/llama-index-readers-elasticsearch/
- Elasticsearch + LlamaIndex Guide: https://www.elastic.co/search-labs/blog/elasticsearch-llamaindex-ingest-data

### Index Querying

ElasticsearchReader supports full Elasticsearch JSON Query DSL for flexible querying.

**Query DSL Support:**
- `match_all`: Retrieve all documents
- `match`: Text matching queries
- `term`: Exact term matching
- `bool`: Boolean combinations of queries
- `range`: Range queries for numeric/date fields
- All other Elasticsearch query types

### Bulk Loading

**Performance Configuration:**
- `batch_size`: Parameter for bulk indexing (default: 200)
- VectorStoreIndex generates and inserts vectors in batches of 2048 nodes by default

### Field Mapping

**Supported Fields:**
- `field`: Field in the document to retrieve text from (required)
- `query`: Elasticsearch JSON query DSL object (optional)
- `embedding_field`: Field containing embeddings (optional)
- `metadata_fields`: List of fields to include as metadata (optional)

### Configuration Options

**Installation:**
```bash
pip install llama-index-readers-elasticsearch
```

**Key Parameters:**
- `endpoint`: URL of Elasticsearch/OpenSearch cluster (required)
- `index`: Name of the index (required)
- `httpx_client_args`: Optional additional arguments for httpx.Client

### Code Examples

#### Example 1: Basic ElasticsearchReader Setup
```python
from llama_index.core.schema import Document
from llama_index.readers.elasticsearch import ElasticsearchReader

# Initialize ElasticsearchReader
reader = ElasticsearchReader(
    endpoint="http://localhost:9200",
    index="my_index",
    httpx_client_args={
        "timeout": 10
    }
)

# Load all documents
documents = reader.load_data(
    field="content",
    query={"query": {"match_all": {}}}
)

print(f"Loaded {len(documents)} documents")
```

#### Example 2: Using Query DSL for Filtering
```python
from llama_index.readers.elasticsearch import ElasticsearchReader

reader = ElasticsearchReader(
    endpoint="https://my-cluster.es.cloud:9243",
    index="articles"
)

# Query with text matching
documents = reader.load_data(
    field="body",
    query={
        "query": {
            "match": {
                "category": {
                    "query": "technology"
                }
            }
        }
    },
    metadata_fields=["title", "author", "published_date"]
)
```

#### Example 3: Complex Query with Boolean Logic
```python
from llama_index.readers.elasticsearch import ElasticsearchReader
from datetime import datetime, timedelta

reader = ElasticsearchReader(
    endpoint="http://localhost:9200",
    index="news_articles"
)

# Complex query with boolean logic and date range
one_month_ago = (datetime.now() - timedelta(days=30)).isoformat()

documents = reader.load_data(
    field="text",
    query={
        "query": {
            "bool": {
                "must": [
                    {"match": {"category": "AI"}},
                    {"range": {
                        "published_date": {
                            "gte": one_month_ago
                        }
                    }}
                ],
                "must_not": [
                    {"term": {"status": "archived"}}
                ]
            }
        },
        "sort": [
            {"published_date": {"order": "desc"}}
        ]
    },
    metadata_fields=["title", "author", "category", "published_date"]
)
```

#### Example 4: Using with Vector Embeddings
```python
from llama_index.readers.elasticsearch import ElasticsearchReader
from llama_index.core import VectorStoreIndex

reader = ElasticsearchReader(
    endpoint="http://localhost:9200",
    index="document_embeddings"
)

# Load documents with existing embeddings
documents = reader.load_data(
    field="content",
    query={"query": {"match_all": {}}},
    embedding_field="content_vector",
    metadata_fields=["source", "doc_type", "created_at"]
)

# Create index
index = VectorStoreIndex.from_documents(documents)
```

#### Example 5: Bulk Loading with Pagination
```python
from llama_index.readers.elasticsearch import ElasticsearchReader
from llama_index.vector_stores.elasticsearch import ElasticsearchStore

# Set up for bulk operations
reader = ElasticsearchReader(
    endpoint="http://localhost:9200",
    index="large_dataset"
)

# Load in batches
batch_size = 1000
documents = reader.load_data(
    field="text",
    query={
        "query": {"match_all": {}},
        "size": batch_size
    }
)

# Store with batch configuration
es_store = ElasticsearchStore(
    index_name="vector_index",
    es_url="http://localhost:9200",
    batch_size=200  # Bulk indexing batch size
)
```

---

## GmailReader

### Overview

GmailReader loads emails from a user's Gmail account. It's part of the Google readers integration package for LlamaIndex.

**Key Resources:**
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/google/
- PyPI Package: https://pypi.org/project/llama-index-readers-google/
- LlamaHub: https://llamahub.ai/l/readers/llama-index-readers-google
- GitHub Source: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-google/llama_index/readers/google/gmail/base.py

### OAuth Setup

**Step-by-Step OAuth Configuration:**

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Navigate to "APIs & Services" -> "Library"
3. Search for "Gmail API" and enable it
4. Go to "APIs & Services" -> "Credentials"
5. Configure OAuth Consent Screen:
   - Choose "Internal" or "External" based on your use case
   - Fill in required information
6. Create OAuth Client ID:
   - Click "Create Credentials" -> "OAuth client ID"
   - Application type: "Desktop app"
   - Download the credentials
7. Save credentials file:
   - Move downloaded file to your working directory
   - Rename to `credentials.json`

**Required Scopes:**
- `https://www.googleapis.com/auth/gmail.readonly` (for read-only access)
- `https://www.googleapis.com/auth/gmail.modify` (for full access)

### Message Loading

GmailReader's `load_data()` method loads emails from the user's account with various filtering options.

**Key Features:**
- Load emails by query string
- Filter by date range
- Limit number of messages
- Include/exclude attachments

### historyId for Incremental Sync

**Gmail API historyId Feature:**
- Gmail API supports incremental synchronization using `historyId`
- Each message/mailbox state has a unique `historyId`
- `historyId` increases chronologically (but not contiguously)
- Valid for at least a week, sometimes only a few hours in rare cases

**How historyId Works:**
1. Initial sync: Load messages and store the latest `historyId`
2. Subsequent syncs: Use `users.history.list` with stored `historyId`
3. Retrieve only changes since last sync (new messages, deletions, label changes)
4. Update stored `historyId` for next sync

**Gmail API History List:**
```
Method: users.history.list
Endpoint: GET https://www.googleapis.com/gmail/v1/users/{userId}/history
Parameters:
  - startHistoryId: Required. Returns history records after this ID
  - maxResults: Optional. Maximum number of history records to return
  - labelId: Optional. Filter by label
  - historyTypes: Optional. Filter by types (messageAdded, messageDeleted, labelAdded, etc.)
```

**LlamaIndex GmailReader Limitation:**
Based on research, the current LlamaIndex GmailReader implementation **does not have built-in historyId-based incremental sync functionality**. The reader loads emails but doesn't track or utilize `historyId` for efficient updates.

**Workaround Options:**

1. **Extend GmailReader:**
   Create a custom reader that inherits from GmailReader and adds historyId tracking

2. **Use Gmail API Directly:**
   Combine Gmail API's history.list with LlamaIndex's IngestionPipeline

3. **Date-based Filtering:**
   Use query strings to filter messages by date (less efficient than historyId)

### Configuration Options

**Installation:**
```bash
pip install llama-index-readers-google
```

**Authentication Files:**
- `credentials.json`: OAuth client credentials from Google Cloud
- `token.json`: Auto-generated after first authentication (stores refresh token)

### Code Examples

#### Example 1: Basic Gmail Loading
```python
from llama_index.readers.google import GmailReader

# Initialize GmailReader
# First run will open browser for OAuth authentication
gmail_reader = GmailReader()

# Load emails
documents = gmail_reader.load_data()

print(f"Loaded {len(documents)} emails")
```

#### Example 2: Loading with Query Filter
```python
from llama_index.readers.google import GmailReader

gmail_reader = GmailReader()

# Load emails with Gmail query syntax
documents = gmail_reader.load_data(
    query="from:notifications@github.com after:2024/01/01"
)

# Query syntax examples:
# - "is:unread": Unread messages
# - "from:user@example.com": From specific sender
# - "subject:meeting": Messages with subject containing "meeting"
# - "after:2024/01/01": Messages after date
# - "has:attachment": Messages with attachments
```

#### Example 3: Custom historyId Tracking (Conceptual)
```python
from llama_index.readers.google import GmailReader
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import json
import os

class IncrementalGmailReader(GmailReader):
    def __init__(self, history_file="gmail_history.json"):
        super().__init__()
        self.history_file = history_file
        self.last_history_id = self._load_history_id()

    def _load_history_id(self):
        """Load last historyId from file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                return data.get('historyId')
        return None

    def _save_history_id(self, history_id):
        """Save historyId to file"""
        with open(self.history_file, 'w') as f:
            json.dump({'historyId': history_id}, f)

    def load_incremental_data(self):
        """Load only new/changed emails since last sync"""
        # Build Gmail API service
        creds = Credentials.from_authorized_user_file('token.json')
        service = build('gmail', 'v1', credentials=creds)

        if self.last_history_id:
            # Use history.list for incremental sync
            history = service.users().history().list(
                userId='me',
                startHistoryId=self.last_history_id,
                historyTypes=['messageAdded']
            ).execute()

            changes = history.get('history', [])
            message_ids = []

            for change in changes:
                if 'messagesAdded' in change:
                    for msg_added in change['messagesAdded']:
                        message_ids.append(msg_added['message']['id'])

            # Load only new messages
            documents = []
            for msg_id in message_ids:
                # Convert to LlamaIndex Document
                # Implementation depends on GmailReader internals
                pass

            # Update historyId
            if 'historyId' in history:
                self._save_history_id(history['historyId'])

            return documents
        else:
            # First sync - load all and save historyId
            documents = self.load_data()

            # Get current historyId from profile
            profile = service.users().getProfile(userId='me').execute()
            if 'historyId' in profile:
                self._save_history_id(profile['historyId'])

            return documents

# Usage
reader = IncrementalGmailReader()

# First run - full sync
documents = reader.load_incremental_data()

# Subsequent runs - only new emails
new_documents = reader.load_incremental_data()
```

#### Example 4: Using with Ingestion Pipeline
```python
from llama_index.readers.google import GmailReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore

# Initialize Gmail reader
gmail_reader = GmailReader()

# Create pipeline with document store for deduplication
docstore = SimpleDocumentStore()
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512)
    ],
    docstore=docstore
)

# First run - load all emails
documents = gmail_reader.load_data(
    query="after:2024/01/01"
)
nodes = pipeline.run(documents=documents)

# Subsequent runs - pipeline automatically handles duplicates
documents = gmail_reader.load_data(
    query="after:2024/01/01"
)
nodes = pipeline.run(documents=documents)  # Only new emails processed
```

#### Example 5: Gmail + Vector Search
```python
from llama_index.readers.google import GmailReader
from llama_index.core import VectorStoreIndex
import os

os.environ["OPENAI_API_KEY"] = "your-api-key"

# Initialize reader
gmail_reader = GmailReader()

# Load work-related emails
documents = gmail_reader.load_data(
    query="label:work OR label:projects after:2024/01/01"
)

# Create searchable index
index = VectorStoreIndex.from_documents(documents)

# Query emails
query_engine = index.as_query_engine()
response = query_engine.query(
    "What are the key action items from recent project emails?"
)
print(response)
```

---

## Common Patterns

### Document Metadata Structure

LlamaIndex Documents have a consistent structure across all readers:

**Core Document Structure:**
```python
from llama_index.core.schema import Document

document = Document(
    text="Document content here",
    metadata={
        "source": "origin of document",
        "date": "creation or modification date",
        # Reader-specific metadata
    },
    doc_id="unique-identifier",  # Optional, auto-generated if not provided
    excluded_llm_metadata_keys=[],  # Metadata keys to exclude from LLM
    excluded_embed_metadata_keys=[]  # Metadata keys to exclude from embeddings
)
```

**Metadata Best Practices:**
1. Use consistent key naming across readers
2. Include temporal information (dates, timestamps)
3. Add source identifiers (URL, file path, message ID)
4. Include document type or category
5. Use standardized date formats (ISO 8601)

**Common Metadata Fields:**
- `source`: Origin URL, file path, or service name
- `created_at`: Document creation timestamp
- `updated_at`: Last modification timestamp
- `doc_type`: Type of document (article, email, code, etc.)
- `author`: Document creator or sender
- `title`: Document title or subject
- `tags`: List of relevant tags or labels

**Metadata Customization:**
```python
from llama_index.core import Document

# Control what metadata is visible to LLM
document = Document(
    text="Content here",
    metadata={
        "title": "Important Document",
        "internal_id": "DOC-12345",
        "content_hash": "abc123",
        "url": "https://example.com/doc"
    },
    excluded_llm_metadata_keys=["internal_id", "content_hash"],  # Hidden from LLM
    excluded_embed_metadata_keys=["internal_id"]  # Hidden from embeddings
)

# Test what LLM sees
from llama_index.core.schema import MetadataMode
llm_view = document.get_content(metadata_mode=MetadataMode.LLM)
```

### Incremental Sync Approaches

#### 1. Document Store with Hash-Based Deduplication

**Best for:** All readers, automatic change detection

```python
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Initialize components
docstore = SimpleDocumentStore()
vector_store = QdrantVectorStore(...)

# Create pipeline
pipeline = IngestionPipeline(
    transformations=[...],
    docstore=docstore,
    vector_store=vector_store
)

# First run - processes all documents
documents = reader.load_data()
nodes = pipeline.run(documents=documents)

# Subsequent runs - only processes changed documents
documents = reader.load_data()
nodes = pipeline.run(documents=documents)  # Automatic deduplication
```

**How it Works:**
- Each document is hashed based on content
- Docstore tracks document IDs and hashes
- On subsequent runs:
  - New doc_id → Process document
  - Existing doc_id + changed hash → Re-process document
  - Existing doc_id + same hash → Skip document

#### 2. Timestamp-Based Filtering

**Best for:** Readers supporting date queries (Gmail, Elasticsearch, Reddit)

```python
from datetime import datetime, timedelta
import json

class TimestampTracker:
    def __init__(self, state_file="sync_state.json"):
        self.state_file = state_file

    def get_last_sync_time(self):
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return datetime.fromisoformat(state['last_sync'])
        except (FileNotFoundError, KeyError):
            # Default to 30 days ago for first run
            return datetime.now() - timedelta(days=30)

    def update_sync_time(self):
        with open(self.state_file, 'w') as f:
            json.dump({'last_sync': datetime.now().isoformat()}, f)

# Usage with different readers
tracker = TimestampTracker()
last_sync = tracker.get_last_sync_time()

# Gmail
documents = gmail_reader.load_data(
    query=f"after:{last_sync.strftime('%Y/%m/%d')}"
)

# Elasticsearch
documents = es_reader.load_data(
    field="content",
    query={
        "query": {
            "range": {
                "timestamp": {
                    "gte": last_sync.isoformat()
                }
            }
        }
    }
)

tracker.update_sync_time()
```

#### 3. API-Specific Incremental Sync

**Best for:** APIs with native incremental support (Gmail historyId, GitHub ETags)

See individual reader sections for implementation details.

#### 4. Cursor-Based Pagination

**Best for:** Large datasets with stable ordering

```python
class CursorTracker:
    def __init__(self, state_file="cursor_state.json"):
        self.state_file = state_file

    def get_cursor(self, reader_name):
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return state.get(reader_name, {}).get('cursor')
        except FileNotFoundError:
            return None

    def save_cursor(self, reader_name, cursor):
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
        except FileNotFoundError:
            state = {}

        state[reader_name] = {'cursor': cursor}

        with open(self.state_file, 'w') as f:
            json.dump(state, f)

# Example with custom implementation
tracker = CursorTracker()
cursor = tracker.get_cursor('my_reader')

# Load data with cursor
documents, next_cursor = custom_reader.load_data(cursor=cursor)

# Save new cursor
tracker.save_cursor('my_reader', next_cursor)
```

### Error Handling

#### 1. Retry with Exponential Backoff

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=2, max_delay=60):
    """Decorator for retrying with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise

                    delay = min(base_delay * (2 ** retries), max_delay)
                    print(f"Retry {retries}/{max_retries} after {delay}s due to: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3, base_delay=2)
def load_documents_with_retry():
    return reader.load_data()

documents = load_documents_with_retry()
```

#### 2. LlamaIndex Retry Query Engine

```python
from llama_index.core.query_engine import RetryQueryEngine
from llama_index.core.evaluation import GuidelineEvaluator

# Create base query engine
query_engine = index.as_query_engine()

# Create evaluator
evaluator = GuidelineEvaluator(
    guidelines="The response should include specific examples and citations."
)

# Wrap with retry functionality
retry_query_engine = RetryQueryEngine(
    query_engine=query_engine,
    evaluator=evaluator,
    max_retries=3
)

# Query with automatic retry
response = retry_query_engine.query("What are the main findings?")
```

#### 3. Graceful Error Handling in Batch Processing

```python
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_process_with_error_handling(
    items: List[str],
    process_func,
    continue_on_error: bool = True
) -> tuple[List, List]:
    """Process items with error handling"""
    successful = []
    failed = []

    for item in items:
        try:
            result = process_func(item)
            successful.append(result)
        except Exception as e:
            logger.error(f"Failed to process {item}: {e}")
            failed.append({'item': item, 'error': str(e)})

            if not continue_on_error:
                raise

    return successful, failed

# Usage with multiple URLs
urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3"
]

documents, errors = batch_process_with_error_handling(
    urls,
    lambda url: firecrawl_reader.load_data(url=url),
    continue_on_error=True
)

logger.info(f"Successfully processed: {len(documents)}")
logger.info(f"Failed: {len(errors)}")
```

#### 4. Reader-Specific Error Handling

```python
from llama_index.core.schema import Document
import logging

logger = logging.getLogger(__name__)

class RobustReader:
    def __init__(self, reader):
        self.reader = reader

    def load_data_safely(self, **kwargs):
        """Load data with comprehensive error handling"""
        try:
            documents = self.reader.load_data(**kwargs)

            # Validate documents
            valid_docs = []
            for doc in documents:
                if self._validate_document(doc):
                    valid_docs.append(doc)
                else:
                    logger.warning(f"Invalid document skipped: {doc.doc_id}")

            return valid_docs

        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            # Could implement fallback to cached data
            return []

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []

    def _validate_document(self, doc: Document) -> bool:
        """Validate document has required fields"""
        if not doc.text or len(doc.text.strip()) == 0:
            return False

        if doc.metadata is None:
            doc.metadata = {}

        return True

# Usage
robust_gmail = RobustReader(gmail_reader)
documents = robust_gmail.load_data_safely(query="after:2024/01/01")
```

### Caching Strategies

```python
from llama_index.core.storage.cache import SimpleCache
from datetime import timedelta

# Initialize cache with TTL
cache = SimpleCache(ttl=timedelta(hours=24))

def cached_load_data(reader, cache_key, **load_kwargs):
    """Load data with caching"""
    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"Using cached data for {cache_key}")
        return cached_result

    # Load fresh data
    documents = reader.load_data(**load_kwargs)

    # Store in cache
    cache.set(cache_key, documents)

    return documents

# Usage
documents = cached_load_data(
    firecrawl_reader,
    cache_key="firecrawl:example.com",
    url="https://example.com"
)
```

### Workflow Integration Pattern

```python
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from typing import List, Callable

class MultiSourceIngestionWorkflow:
    """Unified workflow for multiple data sources"""

    def __init__(self, transformations: List, docstore, vector_store):
        self.pipeline = IngestionPipeline(
            transformations=transformations,
            docstore=docstore,
            vector_store=vector_store
        )
        self.readers = {}

    def register_reader(self, name: str, reader, load_func: Callable):
        """Register a data source reader"""
        self.readers[name] = {
            'reader': reader,
            'load_func': load_func
        }

    def sync_source(self, source_name: str, **load_kwargs):
        """Sync a specific data source"""
        if source_name not in self.readers:
            raise ValueError(f"Unknown source: {source_name}")

        reader_config = self.readers[source_name]
        load_func = reader_config['load_func']

        try:
            # Load documents
            documents = load_func(**load_kwargs)

            # Process through pipeline
            nodes = self.pipeline.run(documents=documents)

            return {
                'source': source_name,
                'status': 'success',
                'documents': len(documents),
                'nodes': len(nodes)
            }

        except Exception as e:
            return {
                'source': source_name,
                'status': 'error',
                'error': str(e)
            }

    def sync_all(self):
        """Sync all registered sources"""
        results = []
        for source_name in self.readers:
            result = self.sync_source(source_name)
            results.append(result)
        return results

# Usage
workflow = MultiSourceIngestionWorkflow(
    transformations=[
        SentenceSplitter(chunk_size=512),
        TitleExtractor(),
        KeywordExtractor()
    ],
    docstore=docstore,
    vector_store=vector_store
)

# Register readers
workflow.register_reader(
    'firecrawl',
    firecrawl_reader,
    lambda url: firecrawl_reader.load_data(url=url)
)

workflow.register_reader(
    'github',
    github_reader,
    lambda branch='main': github_reader.load_data(branch=branch)
)

workflow.register_reader(
    'reddit',
    reddit_reader,
    lambda **kwargs: reddit_reader.load_data(**kwargs)
)

# Sync specific source
result = workflow.sync_source('firecrawl', url='https://example.com')

# Sync all sources
results = workflow.sync_all()
```

---

## Summary Comparison

| Feature | Firecrawl | GitHub | Reddit | Elasticsearch | Gmail |
|---------|-----------|--------|--------|---------------|-------|
| **Installation** | `llama-index-readers-web` | `llama-index-readers-github` | `llama-index-readers-reddit` | `llama-index-readers-elasticsearch` | `llama-index-readers-google` |
| **Auth Type** | API Key | Personal Access Token | OAuth (PRAW) | Basic/None | OAuth 2.0 |
| **Native Incremental Sync** | No | No | No | No | Yes (via historyId) |
| **Query Language** | URL/Mode | Branch/Path filters | Subreddit/Keywords | Elasticsearch Query DSL | Gmail Query Syntax |
| **Batch Support** | Yes (v2 SDK) | Yes (repo-level) | Yes (post_limit) | Yes (batch_size) | Limited |
| **Metadata Richness** | High | High | Medium | High | High |
| **Rate Limits** | API-dependent | 5000 req/hour | 60 req/min (PRAW) | Cluster-dependent | Gmail API limits |
| **Best For** | Web content | Code repos, issues | Discussions, trends | Existing indexed data | Email archives |

---

## References

### Firecrawl
- Official Documentation: https://docs.firecrawl.dev/
- LlamaIndex Integration: https://docs.firecrawl.dev/integrations/llamaindex
- Python SDK: https://docs.firecrawl.dev/sdks/python
- GitHub Repository: https://github.com/firecrawl/firecrawl
- Blog - Scrape API: https://www.firecrawl.dev/blog/mastering-firecrawl-scrape-endpoint
- Blog - Crawl API: https://www.firecrawl.dev/blog/mastering-the-crawl-endpoint-in-firecrawl

### GitHub
- LlamaIndex API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/github/
- PyPI Package: https://pypi.org/project/llama-index-readers-github/
- Issue Analysis Example: https://docs.llamaindex.ai/en/stable/examples/usecases/github_issue_analysis/
- GitHub API Documentation: https://docs.github.com/en/rest

### Reddit
- LlamaIndex API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/reddit/
- PyPI Package: https://pypi.org/project/llama-index-readers-reddit/
- PRAW Documentation: https://praw.readthedocs.io/
- Reddit API: https://www.reddit.com/dev/api/

### Elasticsearch
- LlamaIndex API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/elasticsearch/
- PyPI Package: https://pypi.org/project/llama-index-readers-elasticsearch/
- Elastic Labs Guide: https://www.elastic.co/search-labs/blog/elasticsearch-llamaindex-ingest-data
- Elasticsearch Query DSL: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html

### Gmail
- LlamaIndex API Reference: https://docs.llamaindex.ai/en/stable/api_reference/readers/google/
- PyPI Package: https://pypi.org/project/llama-index-readers-google/
- Gmail API Documentation: https://developers.google.com/gmail/api
- Gmail API Sync Guide: https://developers.google.com/workspace/gmail/api/guides/sync
- History API Reference: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list

### LlamaIndex Core
- Document Structure: https://docs.llamaindex.ai/en/stable/module_guides/loading/documents_and_nodes/usage_documents/
- Ingestion Pipeline: https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/
- Document Management: https://docs.llamaindex.ai/en/stable/examples/ingestion/document_management_pipeline/
- Metadata Extraction: https://docs.llamaindex.ai/en/stable/examples/metadata_extraction/MetadataExtractionSEC/
- Retry Patterns: https://docs.llamaindex.ai/en/stable/api_reference/query_engine/retry/

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Research Date:** 2025-09-30
