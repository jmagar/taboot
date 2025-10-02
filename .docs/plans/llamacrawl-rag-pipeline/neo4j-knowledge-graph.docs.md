# Neo4j Knowledge Graph Integration with LlamaIndex

## Overview

This document provides comprehensive guidance on integrating Neo4j graph database with LlamaIndex for building knowledge graphs to enhance RAG (Retrieval-Augmented Generation) pipelines. The integration enables structured knowledge representation, relationship-aware retrieval, and multi-hop reasoning over diverse data sources including GitHub, Gmail, Reddit, and other platforms.

---

## 1. KnowledgeGraphIndex in LlamaIndex

### 1.1 Core Concepts

LlamaIndex provides two primary approaches for knowledge graph construction:

1. **KnowledgeGraphIndex** (Legacy): Triple-based representation using subject-predicate-object format
2. **PropertyGraphIndex** (Current): Modern property graph with labeled nodes and rich properties

**Key Resources:**
- LlamaIndex Documentation: https://docs.llamaindex.ai/en/stable/module_guides/indexing/lpg_index_guide/
- Property Graph API: https://docs.llamaindex.ai/en/stable/api_reference/indices/property_graph/
- Neo4j Integration: https://docs.llamaindex.ai/en/stable/examples/property_graph/property_graph_neo4j/

### 1.2 How PropertyGraphIndex Works

The PropertyGraphIndex automates knowledge graph construction by:

1. **Parsing documents** into chunks
2. **Extracting entities and relationships** using LLM-based extractors
3. **Creating graph nodes** with labels and properties
4. **Establishing relationships** between entities
5. **Storing embeddings** for semantic search

Property graph construction performs a series of `kg_extractors` on each text chunk, attaching entities and relations as metadata to each LlamaIndex node.

### 1.3 Configuration and Setup

#### Basic Setup

```python
from llama_index.core import PropertyGraphIndex, Document

# Simplest approach - uses defaults
documents = [Document(text="Your text here")]
index = PropertyGraphIndex.from_documents(documents)
```

#### Production Setup with Neo4j

```python
from llama_index.core import PropertyGraphIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
import os

# Configure graph store
graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)

# Create index with custom configuration
index = PropertyGraphIndex.from_documents(
    documents,
    embed_model=OpenAIEmbedding(model_name="text-embedding-3-small"),
    kg_extractors=[
        SchemaLLMPathExtractor(
            llm=OpenAI(model="gpt-3.5-turbo", temperature=0.0)
        )
    ],
    property_graph_store=graph_store,
    show_progress=True,
)
```

#### Loading from Existing Graph

```python
index = PropertyGraphIndex.from_existing(
    property_graph_store=graph_store,
    llm=OpenAI(model="gpt-3.5-turbo", temperature=0.3),
    embed_model=OpenAIEmbedding(model_name="text-embedding-3-small"),
)
```

### 1.4 Entity Extraction Configuration

LlamaIndex supports multiple extraction strategies that can be combined:

**Key Resources:**
- Comparing Extractors: https://docs.llamaindex.ai/en/stable/examples/property_graph/Dynamic_KG_Extraction/
- Knowledge Graph Index Guide: https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/KnowledgeGraphDemo/

---

## 2. Neo4j Python Driver

### 2.1 Connection Patterns

The Neo4j Python driver provides thread-safe, connection-pooling capabilities for database interaction.

**Official Documentation:**
- Python Driver Manual: https://neo4j.com/docs/python-manual/current/
- API Reference: https://neo4j.com/docs/api/python-driver/current/api.html
- Connection Guide: https://neo4j.com/docs/python-manual/current/connect/

#### Basic Connection

```python
from neo4j import GraphDatabase

# Create driver (thread-safe, reusable)
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

# Verify connectivity
driver.verify_connectivity()
```

#### Production Connection with Environment Variables

```python
import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD")
    ),
    encrypted=True,
    trust="TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"
)
```

### 2.2 Transaction Management

**Official Documentation:**
- Transaction Guide: https://neo4j.com/docs/python-manual/current/transactions/
- Concurrent Transactions: https://neo4j.com/docs/python-manual/current/concurrency/
- Transaction Management Course: https://graphacademy.neo4j.com/courses/drivers-python/3-in-production/1-transaction-management/

#### Three Transaction Approaches

##### 1. execute_query() - Simplest Approach

```python
# One-liner for simple queries
records, summary, keys = driver.execute_query(
    "MATCH (p:Person) WHERE p.name = $name RETURN p",
    name="Alice",
    database_="neo4j"
)
```

##### 2. Session-Based Transactions - Recommended

```python
def create_person_node(tx, name, age):
    result = tx.run(
        "CREATE (p:Person {name: $name, age: $age}) RETURN p",
        name=name, age=age
    )
    return result.single()[0]

def get_person_by_name(tx, name):
    result = tx.run(
        "MATCH (p:Person {name: $name}) RETURN p",
        name=name
    )
    return [record["p"] for record in result]

# Use with session
with driver.session() as session:
    # Write transaction
    person = session.execute_write(create_person_node, "Alice", 30)

    # Read transaction
    results = session.execute_read(get_person_by_name, "Alice")
```

##### 3. Manual Transaction Control - Advanced

```python
with driver.session() as session:
    tx = session.begin_transaction()
    try:
        tx.run("CREATE (p:Person {name: $name})", name="Bob")
        tx.run("CREATE (p:Person {name: $name})", name="Charlie")
        tx.commit()
    except Exception as e:
        tx.rollback()
        raise e
```

### 2.3 Transaction Best Practices

1. **Driver is Expensive**: Create once, reuse throughout application
2. **Automatic Retry**: Transaction functions automatically retry on transient failures
3. **Idempotency Required**: Functions may execute multiple times
4. **One Transaction Per Session**: Chain transactions sequentially
5. **Session Constraints**: Use multiple sessions for concurrent transactions

### 2.4 Cypher Query Basics

**Official Documentation:**
- Cypher Manual: https://neo4j.com/docs/cypher-manual/current/
- Pattern Syntax: https://neo4j.com/docs/cypher-manual/current/patterns/

#### Essential Cypher Patterns

```cypher
-- Create nodes
CREATE (p:Person {name: "Alice", age: 30})

-- Create relationships
CREATE (p:Person {name: "Alice"})-[:KNOWS]->(p2:Person {name: "Bob"})

-- Match patterns
MATCH (p:Person)-[:KNOWS]->(friend:Person)
WHERE p.name = "Alice"
RETURN friend

-- Update properties
MATCH (p:Person {name: "Alice"})
SET p.age = 31

-- Delete nodes and relationships
MATCH (p:Person {name: "Alice"})-[r:KNOWS]->()
DELETE r, p
```

### 2.5 Async Support

```python
from neo4j import AsyncGraphDatabase

# Create async driver
driver = AsyncGraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)

# Use with await
async with driver.session() as session:
    result = await session.execute_read(get_person_by_name, "Alice")
```

---

## 3. Graph Schema Design for Multi-Source Data

### 3.1 Schema Design Principles

**Official Resources:**
- Data Modeling Guide: https://neo4j.com/docs/getting-started/data-modeling/
- Tutorial: https://neo4j.com/docs/getting-started/data-modeling/tutorial-data-modeling/
- Graph Database Concepts: https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/

#### Key Principles

1. **Query-Driven Design**: Design based on access patterns and user stories
2. **Entity Identification**: Extract nouns from requirements as potential nodes
3. **Relationship Discovery**: Extract verbs describing connections
4. **Iterative Refinement**: Test, measure performance, refactor
5. **Schema-Optional**: Neo4j allows schema evolution without rigid constraints

### 3.2 Multi-Source Schema Design

For LlamaCrawl RAG pipeline integrating GitHub, Gmail, Reddit, and other sources:

#### Node Labels

```cypher
-- Content Nodes
(:Document)        -- Base content unit
(:GitHubIssue)     -- GitHub issue
(:GitHubPR)        -- GitHub pull request
(:GitHubComment)   -- Comments on issues/PRs
(:Email)           -- Gmail message
(:RedditPost)      -- Reddit submission
(:RedditComment)   -- Reddit comment
(:CodeFile)        -- Source code file
(:Commit)          -- Git commit

-- Entity Nodes
(:Person)          -- Individual (author, committer, email sender)
(:Organization)    -- Company or org
(:Repository)      -- GitHub repository
(:Project)         -- Logical project grouping
(:Topic)           -- Subject matter or tag
(:Location)        -- Geographic location
(:Technology)      -- Programming language, framework, tool

-- Metadata Nodes
(:Source)          -- Data source identifier
(:Timestamp)       -- Time-based grouping
(:Label)           -- GitHub label or tag
```

#### Relationship Types

```cypher
-- Authorship and Contribution
(:Person)-[:AUTHORED]->(:Document)
(:Person)-[:COMMITTED]->(:Commit)
(:Person)-[:SENT]->(:Email)
(:Person)-[:POSTED]->(:RedditPost)
(:Person)-[:COMMENTED_ON]->(:GitHubIssue)

-- Content Relationships
(:Document)-[:REFERENCES]->(:Document)
(:Email)-[:REPLIES_TO]->(:Email)
(:RedditComment)-[:REPLIES_TO]->(:RedditPost)
(:GitHubPR)-[:CLOSES]->(:GitHubIssue)
(:GitHubPR)-[:MODIFIES]->(:CodeFile)
(:Commit)-[:INCLUDES]->(:CodeFile)

-- Organizational
(:Document)-[:BELONGS_TO]->(:Repository)
(:Repository)-[:OWNED_BY]->(:Organization)
(:Person)-[:MEMBER_OF]->(:Organization)
(:Document)-[:TAGGED_WITH]->(:Topic)
(:Document)-[:LABELED_WITH]->(:Label)

-- Temporal
(:Document)-[:CREATED_AT]->(:Timestamp)
(:Document)-[:UPDATED_AT]->(:Timestamp)

-- Semantic
(:Document)-[:MENTIONS]->(:Person)
(:Document)-[:DISCUSSES]->(:Topic)
(:Document)-[:USES]->(:Technology)
(:Document)-[:RELATED_TO]->(:Document)
(:Document)-[:SIMILAR_TO]->(:Document)

-- Source Tracking
(:Document)-[:FROM_SOURCE]->(:Source)
```

#### Properties Design

```cypher
// Person node
{
  id: "unique_identifier",
  name: "John Doe",
  email: "john@example.com",
  github_username: "johndoe",
  reddit_username: "john_reddit",
  avatar_url: "https://...",
  created_at: datetime("2023-01-01T00:00:00Z")
}

// Document node (base)
{
  id: "doc_123",
  title: "Issue title or email subject",
  content: "Full text content",
  embedding: [0.1, 0.2, ...],  // Vector embedding
  content_hash: "sha256_hash",
  word_count: 500,
  created_at: datetime("2023-01-01T00:00:00Z"),
  updated_at: datetime("2023-01-02T00:00:00Z"),
  source_type: "github" | "gmail" | "reddit",
  url: "https://github.com/..."
}

// GitHubIssue (inherits Document properties)
{
  issue_number: 123,
  state: "open" | "closed",
  labels: ["bug", "enhancement"],
  milestone: "v1.0",
  assignees: ["user1", "user2"],
  comments_count: 5,
  reactions: {"+1": 10, "heart": 3}
}

// Email
{
  message_id: "unique_message_id",
  thread_id: "thread_id",
  subject: "Email subject",
  from: "sender@example.com",
  to: ["recipient@example.com"],
  cc: ["cc@example.com"],
  has_attachments: true,
  folder: "inbox"
}

// RedditPost
{
  post_id: "reddit_id",
  subreddit: "r/programming",
  score: 150,
  upvote_ratio: 0.95,
  num_comments: 20,
  is_self: true,
  permalink: "/r/programming/..."
}
```

### 3.3 Schema Constraints and Indexes

```cypher
-- Uniqueness constraints
CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT repo_name IF NOT EXISTS
FOR (r:Repository) REQUIRE r.full_name IS UNIQUE;

-- Indexes for traversal starting points
CREATE INDEX person_email IF NOT EXISTS
FOR (p:Person) ON (p.email);

CREATE INDEX document_created IF NOT EXISTS
FOR (d:Document) ON (d.created_at);

CREATE INDEX document_source IF NOT EXISTS
FOR (d:Document) ON (d.source_type);

-- Full-text search indexes
CREATE FULLTEXT INDEX document_content IF NOT EXISTS
FOR (d:Document) ON EACH [d.title, d.content];

CREATE FULLTEXT INDEX person_name IF NOT EXISTS
FOR (p:Person) ON EACH [p.name, p.email];

-- Vector index for embeddings
CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
FOR (d:Document) ON (d.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
```

---

## 4. Entity Extraction Patterns

### 4.1 Automatic vs. Manual Extraction

**Key Resources:**
- Comparing Extractors: https://docs.llamaindex.ai/en/stable/examples/property_graph/Dynamic_KG_Extraction/
- Knowledge Graph Guide: https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/KnowledgeGraphDemo/
- Customizing Extraction: https://www.llamaindex.ai/blog/customizing-property-graph-index-in-llamaindex

#### Extraction Approaches

1. **Fully Automatic (Free-Form)**: LLM infers entities, relationships, and schema
2. **Schema-Guided**: Define allowed types and relationships
3. **Hybrid**: Combine automatic discovery with schema validation

### 4.2 SimpleLLMPathExtractor (Free-Form)

Best for exploratory analysis and capturing diverse relationships without predefined structure.

```python
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.llms.openai import OpenAI

kg_extractor = SimpleLLMPathExtractor(
    llm=OpenAI(model="gpt-4", temperature=0.0),
    max_paths_per_chunk=10,  # Max relationships to extract per chunk
    num_workers=4,            # Parallel processing
    show_progress=True,
)

# Use in index
index = PropertyGraphIndex.from_documents(
    documents,
    kg_extractors=[kg_extractor],
    property_graph_store=graph_store,
)
```

**Characteristics:**
- Produces diverse relationships
- May lack consistency in naming
- Good for initial exploration
- Higher recall, lower precision

### 4.3 SchemaLLMPathExtractor (Structured)

Best for well-defined domains requiring consistency and validation.

```python
from typing import Literal
from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
from llama_index.llms.openai import OpenAI

# Define entity types
entities = Literal[
    "PERSON",
    "ORGANIZATION",
    "REPOSITORY",
    "TECHNOLOGY",
    "DOCUMENT",
    "TOPIC",
    "LOCATION"
]

# Define relationship types
relations = Literal[
    "AUTHORED",
    "BELONGS_TO",
    "MEMBER_OF",
    "MENTIONS",
    "REFERENCES",
    "USES",
    "DISCUSSES",
    "RELATED_TO"
]

# Define schema (which entities connect via which relationships)
schema = {
    "PERSON": ["AUTHORED", "MEMBER_OF", "MENTIONS"],
    "ORGANIZATION": ["MEMBER_OF"],
    "REPOSITORY": ["BELONGS_TO", "USES"],
    "TECHNOLOGY": ["USES"],
    "DOCUMENT": ["AUTHORED", "BELONGS_TO", "REFERENCES", "MENTIONS", "DISCUSSES"],
    "TOPIC": ["DISCUSSES"],
    "LOCATION": ["MENTIONS"],
}

kg_extractor = SchemaLLMPathExtractor(
    llm=OpenAI(model="gpt-4", temperature=0.0),
    possible_entities=entities,
    possible_relations=relations,
    kg_validation_schema=schema,
    strict=True,  # Reject triplets outside schema
    num_workers=4,
    max_triplets_per_chunk=10,
)
```

**Characteristics:**
- Enforces consistency
- Better precision
- Requires domain knowledge
- Predictable output structure

### 4.4 DynamicLLMPathExtractor (Balanced)

Balances structure and flexibility by adapting to discovered patterns.

```python
from llama_index.core.indices.property_graph import DynamicLLMPathExtractor

kg_extractor = DynamicLLMPathExtractor(
    llm=OpenAI(model="gpt-4", temperature=0.0),
    max_triplets_per_chunk=10,
    num_workers=4,
    allowed_entity_types=["PERSON", "ORGANIZATION", "TECHNOLOGY"],  # Optional
    allowed_relation_types=["WORKS_FOR", "USES", "CREATED"],        # Optional
)
```

### 4.5 Combining Multiple Extractors

```python
# Combine extractors for comprehensive extraction
from llama_index.core.indices.property_graph import (
    SimpleLLMPathExtractor,
    SchemaLLMPathExtractor,
    ImplicitPathExtractor
)

extractors = [
    # Structured extraction with schema
    SchemaLLMPathExtractor(
        llm=llm,
        possible_entities=entities,
        possible_relations=relations,
        kg_validation_schema=schema,
        strict=False,  # Allow additional triplets
    ),
    # Catch implicit relationships from node structure
    ImplicitPathExtractor(),
]

index = PropertyGraphIndex.from_documents(
    documents,
    kg_extractors=extractors,
    property_graph_store=graph_store,
)
```

### 4.6 Custom Extraction for Multi-Source Data

```python
# GitHub-specific schema
github_entities = Literal["ISSUE", "PR", "COMMIT", "PERSON", "REPOSITORY"]
github_relations = Literal["OPENED", "CLOSED", "MERGED", "COMMITTED", "REVIEWED"]

# Email-specific schema
email_entities = Literal["EMAIL", "PERSON", "THREAD", "ATTACHMENT"]
email_relations = Literal["SENT", "RECEIVED", "REPLIED_TO", "ATTACHED"]

# Reddit-specific schema
reddit_entities = Literal["POST", "COMMENT", "SUBREDDIT", "USER"]
reddit_relations = Literal["POSTED", "COMMENTED", "UPVOTED", "BELONGS_TO"]

# Create source-specific extractors
github_extractor = SchemaLLMPathExtractor(
    llm=llm,
    possible_entities=github_entities,
    possible_relations=github_relations,
    kg_validation_schema={...}
)

email_extractor = SchemaLLMPathExtractor(
    llm=llm,
    possible_entities=email_entities,
    possible_relations=email_relations,
    kg_validation_schema={...}
)

# Route documents to appropriate extractor based on source
def get_extractor_for_source(doc):
    if doc.metadata.get("source") == "github":
        return github_extractor
    elif doc.metadata.get("source") == "gmail":
        return email_extractor
    # ... handle other sources
```

---

## 5. Query Patterns: Traversing Relationships for RAG

### 5.1 GraphRAG Retrieval Patterns

**Key Resources:**
- GraphRAG Field Guide: https://neo4j.com/blog/developer/graphrag-field-guide-rag-patterns/
- Neo4j GraphRAG Python: https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html
- Enriching Vector Search: https://medium.com/neo4j/enriching-vector-search-with-graph-traversal-using-the-neo4j-genai-package-79794bc440c4

#### Three Primary Retrieval Patterns

1. **Vector-Only Retrieval**: Traditional similarity search
2. **Graph-Enhanced Retrieval**: Vector search + graph traversal
3. **Text2Cypher**: Natural language to Cypher query generation

### 5.2 Vector + Graph Traversal Pattern

Combines semantic similarity with relationship-based context.

```python
from neo4j_graphrag.retrievers import VectorCypherRetriever

# Define Cypher query for graph traversal
retrieval_query = """
// Start with matched document from vector search
MATCH (node)
WHERE node.id = $node_id

// Expand to related content
OPTIONAL MATCH (node)-[:AUTHORED]->(author:Person)
OPTIONAL MATCH (node)-[:REFERENCES]->(ref:Document)
OPTIONAL MATCH (node)-[:DISCUSSES]->(topic:Topic)
OPTIONAL MATCH (node)-[:BELONGS_TO]->(repo:Repository)

// Return enriched context
RETURN
  node.content as content,
  node.title as title,
  author.name as author_name,
  collect(DISTINCT ref.title) as referenced_docs,
  collect(DISTINCT topic.name) as topics,
  repo.full_name as repository
"""

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="document_embeddings",
    retrieval_query=retrieval_query,
    embedder=embedder,
    result_formatter=format_search_results
)

# Query
results = retriever.search(
    query_text="How to implement authentication?",
    top_k=5
)
```

### 5.3 Hybrid Cypher Retriever

Combines vector search with full-text search and graph traversal.

```python
from neo4j_graphrag.retrievers import HybridCypherRetriever

retrieval_query = """
MATCH (node)-[:AUTHORED]->(author:Person)
MATCH (node)-[:TAGGED_WITH]->(tag:Topic)
RETURN
  node.content as text,
  node.score as score,
  author.name as author,
  collect(tag.name) as tags
"""

retriever = HybridCypherRetriever(
    driver=driver,
    vector_index_name="document_embeddings",
    fulltext_index_name="document_content",
    retrieval_query=retrieval_query,
    embedder=embedder,
)

results = retriever.search(
    query_text="authentication best practices",
    top_k=10
)
```

### 5.4 Text2Cypher Pattern

Converts natural language queries to Cypher using LLM.

**Key Resources:**
- Text2Cypher Retriever: https://medium.com/neo4j/effortless-rag-with-text2cypherretriever-cb1a781ca53c

```python
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OpenAILLM

# Define schema for LLM context
schema = """
Node Labels:
- Document (properties: id, title, content, created_at, source_type)
- Person (properties: id, name, email, github_username)
- Repository (properties: full_name, description, language)
- Topic (properties: name, category)

Relationships:
- (Person)-[:AUTHORED]->(Document)
- (Document)-[:BELONGS_TO]->(Repository)
- (Document)-[:DISCUSSES]->(Topic)
- (Document)-[:REFERENCES]->(Document)
"""

retriever = Text2CypherRetriever(
    driver=driver,
    llm=OpenAILLM(model_name="gpt-4"),
    neo4j_schema=schema,
)

# Natural language query automatically converted to Cypher
results = retriever.search(
    query_text="Find all documents about authentication written by John Doe"
)
```

### 5.5 Multi-Hop Traversal Patterns

```cypher
-- Find related documents through shared authors and topics
MATCH (query_doc:Document {id: $doc_id})
MATCH (query_doc)-[:AUTHORED]->(author:Person)
MATCH (query_doc)-[:DISCUSSES]->(topic:Topic)
MATCH (author)-[:AUTHORED]->(related:Document)
MATCH (related)-[:DISCUSSES]->(topic)
WHERE related.id <> $doc_id
RETURN DISTINCT related, count(*) as relevance_score
ORDER BY relevance_score DESC
LIMIT 10

-- Find expert contributors on a topic
MATCH (topic:Topic {name: $topic_name})
MATCH (doc:Document)-[:DISCUSSES]->(topic)
MATCH (author:Person)-[:AUTHORED]->(doc)
WITH author, count(doc) as doc_count, avg(doc.score) as avg_quality
WHERE doc_count > 3
RETURN author.name, author.email, doc_count, avg_quality
ORDER BY avg_quality DESC, doc_count DESC
LIMIT 5

-- Find conversation threads (email or comments)
MATCH path = (start:Email {id: $email_id})<-[:REPLIES_TO*]-(reply:Email)
RETURN nodes(path) as thread
ORDER BY length(path) DESC

-- Find cross-source references (GitHub issue mentioned in email)
MATCH (email:Email)-[:MENTIONS]->(issue:GitHubIssue)
MATCH (issue)-[:BELONGS_TO]->(repo:Repository)
RETURN email, issue, repo

-- Temporal relationship discovery
MATCH (d1:Document)-[:REFERENCES]->(d2:Document)
WHERE d1.created_at > d2.created_at
WITH d2, collect(d1) as citing_docs, count(d1) as citation_count
WHERE citation_count > 5
RETURN d2.title, d2.url, citation_count, citing_docs
ORDER BY citation_count DESC
```

### 5.6 LlamaIndex Query Engine Integration

```python
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import KnowledgeGraphRAGRetriever

# Create graph-aware retriever
graph_rag_retriever = KnowledgeGraphRAGRetriever(
    storage_context=storage_context,
    verbose=True,
    with_nl2graphquery=True,  # Enable natural language to graph query
    graph_traversal_depth=2,   # Multi-hop depth
)

# Create query engine
query_engine = RetrieverQueryEngine.from_args(
    graph_rag_retriever,
    llm=llm,
    response_mode="tree_summarize"
)

# Query with graph-enhanced retrieval
response = query_engine.query(
    "What are the main authentication patterns discussed by contributors in the security repository?"
)
```

### 5.7 PropertyGraphIndex Retriever Modes

```python
from llama_index.core import PropertyGraphIndex

index = PropertyGraphIndex.from_existing(
    property_graph_store=graph_store,
)

# Mode 1: Vector similarity only
vector_retriever = index.as_retriever(
    include_text=True,
    similarity_top_k=5,
)

# Mode 2: Graph traversal with embeddings
graph_retriever = index.as_retriever(
    include_text=True,
    similarity_top_k=5,
    kg_retriever_kwargs={
        "retriever_mode": "keyword",  # or "embedding" or "hybrid"
        "include_properties": True,
    }
)

# Mode 3: Query engine for natural language
query_engine = index.as_query_engine(
    include_text=True,
    response_mode="tree_summarize",
    embedding_mode="hybrid",
)
```

---

## 6. Integration Pattern: LlamaIndex with Neo4j Backend

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  (Query Interface, API, Chat UI)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  LlamaIndex Layer                            │
│  - PropertyGraphIndex                                        │
│  - KnowledgeGraphQueryEngine                                │
│  - Embeddings (OpenAI/HuggingFace)                          │
│  - LLM (GPT-4, Claude, etc.)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Neo4jPropertyGraphStore                           │
│  - Connection Management                                     │
│  - Cypher Query Execution                                   │
│  - Transaction Handling                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Neo4j Database                               │
│  - Graph Storage                                             │
│  - Vector Indexes                                            │
│  - Full-text Indexes                                         │
│  - ACID Transactions                                         │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Complete Integration Example

```python
import os
from typing import List
from llama_index.core import Document, PropertyGraphIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.indices.property_graph import (
    SchemaLLMPathExtractor,
    SimpleLLMPathExtractor,
)

# 1. Configure Neo4j Connection
graph_store = Neo4jPropertyGraphStore(
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    url=os.getenv("NEO4J_URI"),
    database=os.getenv("NEO4J_DATABASE", "neo4j"),
)

# 2. Configure LLM and Embeddings
llm = OpenAI(
    model="gpt-4",
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY")
)

embed_model = OpenAIEmbedding(
    model_name="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

# 3. Define Knowledge Graph Extractors
from typing import Literal

# Schema for multi-source data
entities = Literal[
    "PERSON", "ORGANIZATION", "REPOSITORY", "DOCUMENT",
    "TOPIC", "TECHNOLOGY", "LOCATION", "EMAIL", "ISSUE", "PR"
]

relations = Literal[
    "AUTHORED", "BELONGS_TO", "MEMBER_OF", "MENTIONS",
    "REFERENCES", "DISCUSSES", "USES", "REPLIED_TO",
    "CLOSED", "MERGED", "REVIEWED"
]

schema = {
    "PERSON": ["AUTHORED", "MEMBER_OF", "REVIEWED"],
    "ORGANIZATION": [],
    "REPOSITORY": ["BELONGS_TO"],
    "DOCUMENT": ["AUTHORED", "BELONGS_TO", "REFERENCES", "DISCUSSES", "MENTIONS"],
    "TOPIC": [],
    "TECHNOLOGY": [],
    "EMAIL": ["AUTHORED", "REPLIED_TO"],
    "ISSUE": ["AUTHORED", "BELONGS_TO", "MENTIONS"],
    "PR": ["AUTHORED", "CLOSED", "MERGED", "REFERENCES"],
}

kg_extractors = [
    SchemaLLMPathExtractor(
        llm=llm,
        possible_entities=entities,
        possible_relations=relations,
        kg_validation_schema=schema,
        strict=False,
        num_workers=4,
        max_triplets_per_chunk=15,
    ),
]

# 4. Create PropertyGraphIndex
def create_index(documents: List[Document]) -> PropertyGraphIndex:
    """Create or update knowledge graph index."""

    index = PropertyGraphIndex.from_documents(
        documents=documents,
        llm=llm,
        embed_model=embed_model,
        kg_extractors=kg_extractors,
        property_graph_store=graph_store,
        show_progress=True,
        # Advanced settings
        node_parser=SentenceSplitter(chunk_size=1024, chunk_overlap=200),
    )

    return index

# 5. Load Existing Index
def load_existing_index() -> PropertyGraphIndex:
    """Load index from existing Neo4j graph."""

    index = PropertyGraphIndex.from_existing(
        property_graph_store=graph_store,
        llm=llm,
        embed_model=embed_model,
    )

    return index

# 6. Query Functions
def query_with_retriever(index: PropertyGraphIndex, query: str) -> List:
    """Query using retriever for granular control."""

    retriever = index.as_retriever(
        include_text=True,
        similarity_top_k=10,
        kg_retriever_kwargs={
            "retriever_mode": "hybrid",
            "include_properties": True,
        }
    )

    nodes = retriever.retrieve(query)
    return nodes

def query_with_engine(index: PropertyGraphIndex, query: str) -> str:
    """Query using query engine for complete responses."""

    query_engine = index.as_query_engine(
        include_text=True,
        response_mode="tree_summarize",
        similarity_top_k=10,
    )

    response = query_engine.query(query)
    return response

# 7. Example Usage
if __name__ == "__main__":
    # Sample documents from different sources
    documents = [
        Document(
            text="Authentication implementation in FastAPI...",
            metadata={
                "source": "github",
                "type": "issue",
                "repository": "fastapi/fastapi",
                "author": "johndoe",
                "url": "https://github.com/fastapi/fastapi/issues/123"
            }
        ),
        Document(
            text="Re: Security best practices discussion...",
            metadata={
                "source": "gmail",
                "type": "email",
                "from": "jane@example.com",
                "subject": "Security best practices",
                "thread_id": "thread_123"
            }
        ),
    ]

    # Create index
    print("Creating knowledge graph index...")
    index = create_index(documents)

    # Query examples
    query = "What are authentication best practices discussed by John Doe?"

    # Using retriever
    print("\n=== Retriever Results ===")
    nodes = query_with_retriever(index, query)
    for node in nodes:
        print(f"Score: {node.score:.3f}")
        print(f"Text: {node.text[:200]}...")
        print(f"Metadata: {node.metadata}\n")

    # Using query engine
    print("\n=== Query Engine Response ===")
    response = query_with_engine(index, query)
    print(response)
```

### 6.3 Advanced: Custom Graph Operations

```python
from neo4j import GraphDatabase

class CustomGraphOperations:
    """Custom operations directly on Neo4j for advanced use cases."""

    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def add_semantic_similarity_edges(self, threshold: float = 0.8):
        """Add SIMILAR_TO relationships between documents with high embedding similarity."""

        query = """
        MATCH (d1:Document)
        MATCH (d2:Document)
        WHERE d1.id < d2.id  // Avoid duplicates
        AND d1.embedding IS NOT NULL
        AND d2.embedding IS NOT NULL
        WITH d1, d2,
             gds.similarity.cosine(d1.embedding, d2.embedding) AS similarity
        WHERE similarity >= $threshold
        MERGE (d1)-[r:SIMILAR_TO]->(d2)
        SET r.similarity = similarity
        RETURN count(r) as relationships_created
        """

        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(query, threshold=threshold).single()
            )
            return result["relationships_created"]

    def identify_expert_contributors(self, topic: str, min_contributions: int = 5):
        """Find experts who frequently contribute to a topic."""

        query = """
        MATCH (p:Person)-[:AUTHORED]->(d:Document)-[:DISCUSSES]->(t:Topic {name: $topic})
        WITH p, count(d) as contributions, collect(d) as docs
        WHERE contributions >= $min_contributions
        RETURN p.name as expert,
               p.email as contact,
               contributions,
               [doc IN docs | doc.title][..5] as recent_documents
        ORDER BY contributions DESC
        """

        with self.driver.session() as session:
            result = session.execute_read(
                lambda tx: tx.run(
                    query,
                    topic=topic,
                    min_contributions=min_contributions
                ).data()
            )
            return result

    def create_temporal_clusters(self, time_window_days: int = 30):
        """Group documents by temporal proximity and shared topics."""

        query = """
        MATCH (d1:Document)-[:DISCUSSES]->(t:Topic)<-[:DISCUSSES]-(d2:Document)
        WHERE d1.created_at IS NOT NULL
        AND d2.created_at IS NOT NULL
        AND duration.between(d1.created_at, d2.created_at).days <= $window
        WITH d1, d2, count(t) as shared_topics
        WHERE shared_topics >= 2
        MERGE (d1)-[r:TEMPORALLY_RELATED]->(d2)
        SET r.shared_topics = shared_topics
        RETURN count(r) as temporal_relationships
        """

        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(query, window=time_window_days).single()
            )
            return result["temporal_relationships"]

    def close(self):
        self.driver.close()

# Usage
custom_ops = CustomGraphOperations(
    uri=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD")
)

# Enrich graph with computed relationships
custom_ops.add_semantic_similarity_edges(threshold=0.85)
experts = custom_ops.identify_expert_contributors("authentication", min_contributions=3)
custom_ops.create_temporal_clusters(time_window_days=7)

custom_ops.close()
```

---

## 7. Code Examples: Complete Pipeline

### 7.1 Installation

```bash
# Core dependencies
pip install llama-index
pip install llama-index-graph-stores-neo4j
pip install llama-index-llms-openai
pip install llama-index-embeddings-openai
pip install neo4j

# Optional dependencies
pip install python-dotenv  # Environment management
pip install httpx         # Async HTTP client
```

### 7.2 Environment Configuration

```bash
# .env file
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=llamacrawl

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional: Alternative LLMs
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
```

### 7.3 Multi-Source Ingestion Pipeline

```python
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from llama_index.core import Document
from llama_index.core import PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv

load_dotenv()

@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    entity_types: List[str]
    relation_types: List[str]
    metadata_fields: List[str]

class MultiSourceKnowledgeGraph:
    """Knowledge graph builder for multiple data sources."""

    def __init__(self):
        # Initialize Neo4j connection
        self.graph_store = Neo4jPropertyGraphStore(
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            url=os.getenv("NEO4J_URI"),
            database=os.getenv("NEO4J_DATABASE", "llamacrawl"),
        )

        # Initialize LLM and embeddings
        self.llm = OpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=0.0,
        )

        self.embed_model = OpenAIEmbedding(
            model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )

        # Source configurations
        self.sources = {
            "github": SourceConfig(
                name="github",
                entity_types=["ISSUE", "PR", "COMMIT", "PERSON", "REPOSITORY"],
                relation_types=["OPENED", "CLOSED", "MERGED", "COMMITTED", "REVIEWED"],
                metadata_fields=["issue_number", "state", "labels", "url"]
            ),
            "gmail": SourceConfig(
                name="gmail",
                entity_types=["EMAIL", "PERSON", "THREAD"],
                relation_types=["SENT", "REPLIED_TO"],
                metadata_fields=["message_id", "thread_id", "from", "to", "subject"]
            ),
            "reddit": SourceConfig(
                name="reddit",
                entity_types=["POST", "COMMENT", "SUBREDDIT", "USER"],
                relation_types=["POSTED", "COMMENTED", "BELONGS_TO"],
                metadata_fields=["post_id", "subreddit", "score", "url"]
            ),
        }

        self.index = None

    def ingest_github_issues(self, issues: List[Dict[str, Any]]) -> List[Document]:
        """Convert GitHub issues to LlamaIndex documents."""
        documents = []

        for issue in issues:
            doc = Document(
                text=f"{issue['title']}\n\n{issue['body']}",
                metadata={
                    "source": "github",
                    "type": "issue",
                    "issue_number": issue["number"],
                    "state": issue["state"],
                    "repository": issue["repository"],
                    "author": issue["user"]["login"],
                    "labels": [label["name"] for label in issue.get("labels", [])],
                    "created_at": issue["created_at"],
                    "url": issue["html_url"],
                }
            )
            documents.append(doc)

        return documents

    def ingest_emails(self, emails: List[Dict[str, Any]]) -> List[Document]:
        """Convert Gmail messages to LlamaIndex documents."""
        documents = []

        for email in emails:
            doc = Document(
                text=f"Subject: {email['subject']}\n\n{email['body']}",
                metadata={
                    "source": "gmail",
                    "type": "email",
                    "message_id": email["id"],
                    "thread_id": email["thread_id"],
                    "from": email["from"],
                    "to": email["to"],
                    "subject": email["subject"],
                    "created_at": email["date"],
                }
            )
            documents.append(doc)

        return documents

    def ingest_reddit_posts(self, posts: List[Dict[str, Any]]) -> List[Document]:
        """Convert Reddit posts to LlamaIndex documents."""
        documents = []

        for post in posts:
            doc = Document(
                text=f"{post['title']}\n\n{post.get('selftext', '')}",
                metadata={
                    "source": "reddit",
                    "type": "post",
                    "post_id": post["id"],
                    "subreddit": post["subreddit"],
                    "author": post["author"],
                    "score": post["score"],
                    "num_comments": post["num_comments"],
                    "created_at": datetime.fromtimestamp(post["created_utc"]).isoformat(),
                    "url": f"https://reddit.com{post['permalink']}",
                }
            )
            documents.append(doc)

        return documents

    def build_index(self, documents: List[Document]):
        """Build or update the knowledge graph index."""
        from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
        from typing import Literal

        # Define comprehensive schema
        entities = Literal[
            "PERSON", "ORGANIZATION", "REPOSITORY", "TOPIC",
            "TECHNOLOGY", "ISSUE", "PR", "EMAIL", "POST", "COMMENT"
        ]

        relations = Literal[
            "AUTHORED", "BELONGS_TO", "MEMBER_OF", "MENTIONS",
            "REFERENCES", "DISCUSSES", "USES", "REPLIED_TO",
            "CLOSED", "MERGED", "REVIEWED", "COMMENTED_ON"
        ]

        kg_extractor = SchemaLLMPathExtractor(
            llm=self.llm,
            possible_entities=entities,
            possible_relations=relations,
            strict=False,
            num_workers=4,
            max_triplets_per_chunk=20,
        )

        # Create or update index
        if self.index is None:
            self.index = PropertyGraphIndex.from_documents(
                documents=documents,
                llm=self.llm,
                embed_model=self.embed_model,
                kg_extractors=[kg_extractor],
                property_graph_store=self.graph_store,
                show_progress=True,
            )
        else:
            # Add documents to existing index
            for doc in documents:
                self.index.insert(doc)

    def query(self, query_text: str, top_k: int = 5) -> str:
        """Query the knowledge graph."""
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        query_engine = self.index.as_query_engine(
            include_text=True,
            response_mode="tree_summarize",
            similarity_top_k=top_k,
        )

        response = query_engine.query(query_text)
        return str(response)

    def get_retriever(self, mode: str = "hybrid"):
        """Get retriever for custom query logic."""
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        return self.index.as_retriever(
            include_text=True,
            similarity_top_k=10,
            kg_retriever_kwargs={
                "retriever_mode": mode,  # "hybrid", "keyword", or "embedding"
                "include_properties": True,
            }
        )

# Usage example
def main():
    kg = MultiSourceKnowledgeGraph()

    # Sample data ingestion
    github_issues = [
        {
            "number": 123,
            "title": "Add authentication middleware",
            "body": "We need JWT-based authentication...",
            "state": "open",
            "repository": "myorg/myrepo",
            "user": {"login": "johndoe"},
            "labels": [{"name": "enhancement"}, {"name": "security"}],
            "created_at": "2024-01-15T10:00:00Z",
            "html_url": "https://github.com/myorg/myrepo/issues/123"
        }
    ]

    emails = [
        {
            "id": "email_001",
            "thread_id": "thread_001",
            "from": "jane@example.com",
            "to": ["team@example.com"],
            "subject": "Re: Authentication implementation",
            "body": "I recommend using OAuth 2.0...",
            "date": "2024-01-16T14:30:00Z"
        }
    ]

    reddit_posts = [
        {
            "id": "abc123",
            "title": "Best practices for API authentication",
            "selftext": "What are the current best practices...",
            "subreddit": "programming",
            "author": "pythondev",
            "score": 250,
            "num_comments": 45,
            "created_utc": 1705420800,
            "permalink": "/r/programming/comments/abc123/"
        }
    ]

    # Ingest documents
    print("Ingesting documents from multiple sources...")
    documents = []
    documents.extend(kg.ingest_github_issues(github_issues))
    documents.extend(kg.ingest_emails(emails))
    documents.extend(kg.ingest_reddit_posts(reddit_posts))

    # Build knowledge graph
    print(f"Building knowledge graph from {len(documents)} documents...")
    kg.build_index(documents)

    # Query the graph
    print("\nQuerying knowledge graph...")
    response = kg.query("What are the recommended authentication approaches?")
    print(f"Response: {response}")

if __name__ == "__main__":
    main()
```

### 7.4 Graph-Enhanced RAG Query Example

```python
from typing import List, Dict, Any
from llama_index.core import PropertyGraphIndex
from llama_index.core.schema import NodeWithScore

class GraphEnhancedRAG:
    """RAG system with graph-enhanced retrieval."""

    def __init__(self, index: PropertyGraphIndex):
        self.index = index
        self.retriever = index.as_retriever(
            include_text=True,
            similarity_top_k=10,
            kg_retriever_kwargs={
                "retriever_mode": "hybrid",
                "include_properties": True,
            }
        )

    def retrieve_with_context(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve nodes with enriched graph context."""
        nodes = self.retriever.retrieve(query)

        enriched_results = []
        for node in nodes:
            # Extract metadata and relationships
            result = {
                "text": node.text,
                "score": node.score,
                "metadata": node.metadata,
                "relationships": self._get_relationships(node),
            }
            enriched_results.append(result)

        return enriched_results

    def _get_relationships(self, node: NodeWithScore) -> Dict[str, List[str]]:
        """Extract relationship information from node."""
        # This would query Neo4j directly for relationship details
        # Simplified example:
        relationships = {
            "authors": [],
            "references": [],
            "topics": [],
            "similar_docs": [],
        }

        # In practice, execute Cypher queries to get relationships
        # from the graph_store based on node.id

        return relationships

    def answer_question(self, question: str) -> Dict[str, Any]:
        """Generate answer with source attribution and graph context."""
        # Retrieve relevant nodes
        results = self.retrieve_with_context(question)

        # Build context for LLM
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            context_parts.append(
                f"[Source {i}] {result['text']}\n"
                f"(Score: {result['score']:.3f}, "
                f"Authors: {', '.join(result['relationships']['authors'][:3])})"
            )

        context = "\n\n".join(context_parts)

        # Generate response using query engine
        query_engine = self.index.as_query_engine()
        response = query_engine.query(question)

        return {
            "answer": str(response),
            "sources": results,
            "context": context,
        }

# Usage
rag = GraphEnhancedRAG(kg.index)
result = rag.answer_question("How should I implement authentication in FastAPI?")

print(f"Answer: {result['answer']}")
print(f"\nSources used: {len(result['sources'])}")
for i, source in enumerate(result['sources'][:3], 1):
    print(f"{i}. {source['metadata'].get('url', 'N/A')} (score: {source['score']:.3f})")
```

---

## 8. Performance Optimization

### 8.1 Indexing Strategy

```cypher
-- Create indexes for common query patterns
CREATE INDEX document_source IF NOT EXISTS
FOR (d:Document) ON (d.source_type);

CREATE INDEX document_created IF NOT EXISTS
FOR (d:Document) ON (d.created_at);

CREATE INDEX person_email IF NOT EXISTS
FOR (p:Person) ON (p.email);

-- Full-text search
CREATE FULLTEXT INDEX document_search IF NOT EXISTS
FOR (d:Document) ON EACH [d.title, d.content];

-- Vector similarity
CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
FOR (d:Document) ON (d.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
```

### 8.2 Query Optimization

```python
# Use query result caching
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_query(query_text: str, top_k: int = 5):
    return kg.query(query_text, top_k)

# Batch processing for multiple documents
def batch_ingest(documents: List[Document], batch_size: int = 50):
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        kg.build_index(batch)
        print(f"Processed batch {i//batch_size + 1}")

# Parallel extraction
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor

kg_extractor = SimpleLLMPathExtractor(
    llm=llm,
    num_workers=8,  # Increase for parallel processing
    max_paths_per_chunk=10,
)
```

---

## 9. Monitoring and Maintenance

### 9.1 Graph Statistics

```cypher
-- Count nodes by label
CALL db.labels() YIELD label
CALL apoc.cypher.run('MATCH (:`'+label+'`) RETURN count(*) as count', {})
YIELD value
RETURN label, value.count as count
ORDER BY count DESC;

-- Count relationships by type
CALL db.relationshipTypes() YIELD relationshipType
CALL apoc.cypher.run('MATCH ()-[:`'+relationshipType+'`]->() RETURN count(*) as count', {})
YIELD value
RETURN relationshipType, value.count as count
ORDER BY count DESC;

-- Find orphaned nodes
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) as label, count(n) as count;
```

### 9.2 Health Checks

```python
def check_graph_health(driver):
    """Verify graph database health."""
    with driver.session() as session:
        # Check connectivity
        result = session.run("RETURN 1 as test")
        assert result.single()["test"] == 1

        # Check node count
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()["count"]
        print(f"Total nodes: {node_count}")

        # Check relationship count
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        print(f"Total relationships: {rel_count}")

        return {"nodes": node_count, "relationships": rel_count}
```

---

## 10. Additional Resources

### Official Documentation
- **LlamaIndex**: https://docs.llamaindex.ai/
- **Neo4j Python Driver**: https://neo4j.com/docs/python-manual/current/
- **Neo4j Cypher Manual**: https://neo4j.com/docs/cypher-manual/current/
- **Neo4j Graph Academy**: https://graphacademy.neo4j.com/

### Integration Guides
- **LlamaIndex Neo4j Integration**: https://neo4j.com/labs/genai-ecosystem/llamaindex/
- **Building Knowledge Graphs**: https://www.llamaindex.ai/blog/introducing-the-property-graph-index-a-powerful-new-way-to-build-knowledge-graphs-with-llms
- **GraphRAG Guide**: https://neo4j.com/blog/developer/graphrag-field-guide-rag-patterns/

### Tutorials and Examples
- **Property Graph Index Examples**: https://docs.llamaindex.ai/en/stable/examples/property_graph/
- **Knowledge Graph Cookbook**: https://docs.llamaindex.ai/en/latest/examples/cookbooks/build_knowledge_graph_with_neo4j_llamacloud/
- **Neo4j GraphRAG Python**: https://github.com/neo4j/neo4j-graphrag-python

### Community Resources
- **LlamaIndex GitHub**: https://github.com/run-llama/llama_index
- **Neo4j Community Forum**: https://community.neo4j.com/
- **LlamaIndex Discord**: https://discord.gg/dGcwcsnxhU

---

## Conclusion

This document provides a comprehensive foundation for integrating Neo4j graph database with LlamaIndex to build sophisticated knowledge graphs for RAG applications. The combination of LlamaIndex's PropertyGraphIndex and Neo4j's graph database capabilities enables:

1. **Automated knowledge extraction** from multi-source data
2. **Relationship-aware retrieval** that goes beyond semantic similarity
3. **Multi-hop reasoning** across connected entities
4. **Scalable graph storage** with ACID transactions
5. **Flexible schema evolution** as data sources expand

The patterns and code examples provided can be adapted to specific requirements of the LlamaCrawl RAG pipeline, supporting integration of GitHub, Gmail, Reddit, and other data sources into a unified knowledge graph.
