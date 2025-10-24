# ADR 0001: Adopt Neo4j for Knowledge Graph Storage

- Status: Accepted
- Date: 2025-02-24
- Stakeholders: Core platform, Retrieval, Graph analytics

## Context

We require a graph database to represent entities, relationships, and provenance metadata produced by the extraction tiers. The store must support deep traversals, flexible schema evolution, and Cypher queries used by downstream analytics. Alternatives evaluated included Postgres + pgvector, ArangoDB, and Memgraph.

## Decision

Adopt Neo4j 5.x with the official Python driver and the `neo4j-graph-stores` LlamaIndex integration as the primary knowledge graph store. We will optimize writes via batched `UNWIND` statements and leverage native graph algorithms for enrichment.

## Consequences

- ✅ Mature ecosystem with Cypher, APOC, and Bloom tooling for analysts.
- ✅ Tight integration with LlamaIndex keeps ingestion/adapters simple.
- ⚠️ Requires separate licensing for enterprise features and managed clustering.
- ⚠️ Operational overhead (page cache tuning, backups) compared to Postgres alone.
