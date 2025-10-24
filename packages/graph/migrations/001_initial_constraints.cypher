// Initial Neo4j schema: constraints and indexes
// Per MIGRATIONS.md: use idempotent IF NOT EXISTS clauses
// Per data-model.md: Service, Host, IP, Proxy, Endpoint, Doc nodes

// ============================================================
// Node constraints (unique properties)
// ============================================================

// Service nodes: unique by name
CREATE CONSTRAINT service_name IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

// Host nodes: unique by hostname
CREATE CONSTRAINT host_hostname IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS UNIQUE;

// IP nodes: unique by address
CREATE CONSTRAINT ip_addr IF NOT EXISTS
FOR (i:IP) REQUIRE i.addr IS UNIQUE;

// Proxy nodes: unique by name
CREATE CONSTRAINT proxy_name IF NOT EXISTS
FOR (p:Proxy) REQUIRE p.name IS UNIQUE;

// Doc nodes: unique by doc_id
CREATE CONSTRAINT doc_id IF NOT EXISTS
FOR (d:Doc) REQUIRE d.doc_id IS UNIQUE;

// ============================================================
// Composite indexes for common queries
// ============================================================

// Endpoint lookups by service + method + path
CREATE INDEX endpoint_composite IF NOT EXISTS
FOR (e:Endpoint) ON (e.service, e.method, e.path);

// Doc lookups by source_type (for filtering)
CREATE INDEX doc_source_type IF NOT EXISTS
FOR (d:Doc) ON (d.source_type);

// Doc lookups by created_at (for temporal queries)
CREATE INDEX doc_created_at IF NOT EXISTS
FOR (d:Doc) ON (d.created_at);
