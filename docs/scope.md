1. Scope & Prioritization
The INIT.md lists 15+ data sources (Gmail, Google Drive, YouTube, GitHub, PDFs, etc.). For this initial implementation:
Should we build the complete pipeline framework that can support all readers, but only implement a subset of data sources first?
Or should we focus on end-to-end functionality for just 1-2 data sources to prove the concept?
Which 2-3 data sources are highest priority for your use case?

  - For the initial implementation, let's focus on recreating the pipeline I had created with the modified Firecrawl setup I had. But let's make sure we lay the foundation to easily and quickly add more data sources later. So initially let's have:
    - Firecrawl
    - Github
    - Reddit
    - Elasticsearch
    - Gmail


2. User Interface
How will users interact with this system?
CLI tool for ingestion and querying?
REST API for programmatic access?
Both?
Something else (web UI, chat interface)?

  - Well, I definitely plan to have a WebUI and possibly a chat interface as well, but that's much further down the road, the main way I want to be able to interact with the system is as an MCP (model context protocol) server, which seems llamaindex has made it very easy to set up:
  - https://developers.llamaindex.ai/python/framework/module_guides/mcp/
  - https://developers.llamaindex.ai/python/framework/module_guides/mcp/convert_existing
  - https://developers.llamaindex.ai/python/framework/module_guides/mcp/llamaindex_mcp/

    With this approach do you even need to create an API or CLI? I definitely do want both eventually, but maybe the MCP server can serve as the primary interface initially.


3. Authentication & Credentials
For Google services (Gmail, Drive, Docs, Calendar, Keep), you'll need OAuth:
Do you already have Google Cloud Project credentials?
  - Yes

Should the system support multiple users/accounts, or just your personal account?
  - Just my personal account for now.

For other services (GitHub, Reddit, Feedly) - single account or multi-user?
  - Single account for now.

Ideally, I would like the system to support multiple users/accounts in the future, so let's design the authentication module with that in mind.

4. Data Ingestion Model
One-time bulk import of historical data, then periodic updates?
    - Yes
Continuous sync/monitoring (watching for new emails, files, etc.)?
    - Yes
Manual triggers (user initiates "sync Gmail now")?
    - Yes
Scheduled batch jobs (nightly ingestion)?
    - Yes

5. Query/Retrieval Interface
When querying the RAG system:
What's the expected output format? (Ranked list of sources? Synthesized answer? Both?)
    - I'm thinking both... Maybe the synthesized answer with source attribution.

Should it support filtering by source type? (e.g., "search only Gmail")
    - Yes, definitely.

Hybrid search (combining vector similarity + metadata filters like date ranges)?
   - Yes, that would be ideal. Remember we also have a neo4j graph database for relationship queries. So, ideally I'd like to have a combined query interface that can leverage all these sources seamlessly.




6. MCP Server Interface Design
LlamaIndex MCP servers can expose:
Tools (functions Claude can call, like "ingest_gmail" or "search_documents")
Resources (data sources Claude can read, like "recent_ingestions" or "available_sources")
What tools/resources should the MCP server expose? Suggested Tools:
ingest_source(source_type, params) - Trigger ingestion for a specific source
query_rag(query, filters, sources) - Search with optional filtering
get_ingestion_status() - Check running jobs
list_sources() - Show configured data sources
Suggested Resources:
ingestion_logs - Recent ingestion activity
source_statistics - Document counts per source
Does this match your vision, or do you have other ideas?

    - Do we really need to worry about this currently? I'd really like to focus on just getting the pipeline operational before we build out the full MCP interface.

7. Incremental Sync & Deduplication
For continuous sync (especially Gmail, GitHub, Reddit):
Tracking mechanism: How should we track "last synced" state?
Store timestamps/cursors in Redis?
    - Yes, Redis sounds like a good idea.

Use source-specific mechanisms (Gmail historyId, GitHub since timestamp)?
    - When possible, yes.

Deduplication strategy:
Hash-based detection (if content unchanged, skip re-embedding)?
    - Yes

Update existing vectors vs. create new ones?
    - Update existing vectors when content changes

How to handle edited content (GitHub issues, Reddit edits)?
    - Track edit history and update vectors accordingly

8. Neo4j Graph Schema
You want Neo4j for relationship queries. What relationships matter most? 
    - I'm not too sure, I don't have much experience with Neo4j, I would prefer to graph as much as possible as long as it's not consuming massive amounts of resources. Storage used is a non-factor here.

Examples:
GitHub: (User)-[:AUTHORED]->(Issue)-[:REFERENCES]->(PullRequest)
Gmail: (Email)-[:REPLIED_TO]->(Email), (Person)-[:SENT]->(Email)
Cross-source: (GitHubIssue)-[:MENTIONED_IN]->(Email)

Should we:
Build the graph during ingestion (extract entities/relationships immediately)?
    - Yes
Build it post-ingestion (analyze stored documents later)?
Use LlamaIndex's KnowledgeGraphIndex for automatic extraction?
    - Uh, this sounds like a nobrainer? Yes?

9. Scheduling & Job Management
For scheduled batch jobs:
Job orchestration:
Built-in scheduler (APScheduler, Celery)?
External (cron, Kubernetes CronJobs)?
    - For these two, if we're continuously syncing, we don't really need a scheduling mechanism do we? Let's not worry about scheduling for now..

Trigger via MCP tool call?
    - Yes

Concurrency:
Can multiple sources ingest simultaneously?
    - Yes

Lock mechanism to prevent duplicate jobs?
    - Yes. whatever's simplest.

10. Self-Hosted Firecrawl
For your stock Firecrawl setup:
Will you deploy it in the same docker-compose as the RAG pipeline?
    - Yes, we'll deploy it with the rest of the stack. @docker-compose.yaml
    - Remember we are deploying the stack to my host steamy-wsl via docker context. That host has the RTX 4070 for generating embeddings/reranking

Or separate deployment (LlamaIndex calls Firecrawl API over network)?
Any specific Firecrawl configuration needs (rate limits, crawl depth defaults)?
    - It's my own instance of Firecrawl, so no, we don't need rate limits. Let's have the crawl depth default to 3. And make sure max pages isnt just 100, it should be like 1000.
    - The Firecrawl URL will be: https://firecrawl.tootie.tv


11. Development Environment
Do you want this deployable to steamy-wsl immediately, or develop locally first?
    - We can develop locally, but we will need to deploy the infrastructure immediately (Firecrawl, Redis, Neo4j, Qdrant, and both TEI instances)

Python environment: uv, poetry, pip + venv?
    - uv + pyproject.toml
    
Hot reload during development?
   - Well MCP servers don't support hot reload at the moment. But we're not focusing on that right now. So yes? If we're not building out the MCP interface currently, how exactly are we going to be interacting with the pipeline?



Final Clarifications
Before I summarize for the requirements doc:
12. Error Handling & Resilience
For ingestion failures (API rate limits, network issues, auth failures):
Retry logic with exponential backoff?
    - Yes, definitely.

Dead letter queue for failed items?
    - Yes, a dead letter queue would be useful for later analysis and reprocessing.

Just log and continue?
    - We should log all errors regardless, but not all errors should halt the pipeline.

13. Configuration Management
.env file for secrets (API keys, credentials)?
    - Yes, definitely.
    
YAML/TOML for pipeline config (which sources enabled, crawl settings)?
    - Both, .env for sensitive info and YAML/TOML for general config.

14. Observability
Structured logging (JSON logs)?
    - Yes, definitely.
Metrics (Prometheus-style)?
    - Yes, Prometheus metrics would be useful for monitoring.

Or just basic Python logging for now?
    - Basic logging is fine to start, but we should integrate with Prometheus eventually.

These are quick answers - then I can write up the requirements doc!