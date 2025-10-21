// Neo4j Constraints and Indexes for Taboot Graph Schema
// Execute these queries during initialization (taboot init command)
// All constraints ensure uniqueness and enable fast lookups

// Service node constraints
CREATE CONSTRAINT service_name_unique
IF NOT EXISTS
FOR (s:Service)
REQUIRE s.name IS UNIQUE;

// Host node constraints
CREATE CONSTRAINT host_hostname_unique
IF NOT EXISTS
FOR (h:Host)
REQUIRE h.hostname IS UNIQUE;

// IP node constraints
CREATE CONSTRAINT ip_addr_unique
IF NOT EXISTS
FOR (ip:IP)
REQUIRE ip.addr IS UNIQUE;

// Proxy node constraints
CREATE CONSTRAINT proxy_name_unique
IF NOT EXISTS
FOR (p:Proxy)
REQUIRE p.name IS UNIQUE;

// Endpoint composite index (service + method + path uniqueness)
CREATE INDEX endpoint_composite_idx
IF NOT EXISTS
FOR (e:Endpoint)
ON (e.service, e.method, e.path);

// Performance indexes for common queries

// Index on Service.version for version filtering
CREATE INDEX service_version_idx
IF NOT EXISTS
FOR (s:Service)
ON (s.version);

// Index on extraction_version for reprocessing queries
CREATE INDEX service_extraction_version_idx
IF NOT EXISTS
FOR (s:Service)
ON (s.extraction_version);

CREATE INDEX host_extraction_version_idx
IF NOT EXISTS
FOR (h:Host)
ON (h.extraction_version);

CREATE INDEX ip_extraction_version_idx
IF NOT EXISTS
FOR (ip:IP)
ON (ip.extraction_version);

CREATE INDEX proxy_extraction_version_idx
IF NOT EXISTS
FOR (p:Proxy)
ON (p.extraction_version);

// Index on updated_at for time-based queries
CREATE INDEX service_updated_at_idx
IF NOT EXISTS
FOR (s:Service)
ON (s.updated_at);

CREATE INDEX host_updated_at_idx
IF NOT EXISTS
FOR (h:Host)
ON (h.updated_at);

// Relationship indexes for traversal performance

// Index on DEPENDS_ON relationship properties
CREATE INDEX depends_on_confidence_idx
IF NOT EXISTS
FOR ()-[r:DEPENDS_ON]-()
ON (r.confidence);

// Index on ROUTES_TO relationship properties
CREATE INDEX routes_to_host_idx
IF NOT EXISTS
FOR ()-[r:ROUTES_TO]-()
ON (r.host);

// Index on MENTIONS relationship properties (for chunk lookups)
CREATE INDEX mentions_chunk_id_idx
IF NOT EXISTS
FOR ()-[r:MENTIONS]-()
ON (r.chunk_id);

CREATE INDEX mentions_doc_id_idx
IF NOT EXISTS
FOR ()-[r:MENTIONS]-()
ON (r.doc_id);

// Full-text index on Service names and descriptions for search
CREATE FULLTEXT INDEX service_fulltext_idx
IF NOT EXISTS
FOR (s:Service)
ON EACH [s.name, s.description];

// Full-text index on Host hostnames for search
CREATE FULLTEXT INDEX host_fulltext_idx
IF NOT EXISTS
FOR (h:Host)
ON EACH [h.hostname];

// Verification queries (run after constraint creation to confirm)

// Count constraints
SHOW CONSTRAINTS;

// Count indexes
SHOW INDEXES;

// Expected output:
// - 4 unique constraints (Service.name, Host.hostname, IP.addr, Proxy.name)
// - 1 composite index (Endpoint)
// - 11 property indexes (version, extraction_version, updated_at, confidence, host, chunk_id, doc_id)
// - 2 full-text indexes (Service, Host)
