// Neo4j Constraints and Indexes for Taboot Graph Schema
// Execute these queries during initialization (taboot init command)
// All constraints ensure uniqueness and enable fast lookups

// === CORE ENTITY CONSTRAINTS ===
// These entities span multiple data sources and need unique identification

// Person node constraints (email is unique identifier)
CREATE CONSTRAINT person_email_unique
IF NOT EXISTS
FOR (p:Person)
REQUIRE p.email IS UNIQUE;

// Organization node constraints (name is unique identifier)
CREATE CONSTRAINT organization_name_unique
IF NOT EXISTS
FOR (o:Organization)
REQUIRE o.name IS UNIQUE;

// Place node constraints (name is unique identifier)
CREATE CONSTRAINT place_name_unique
IF NOT EXISTS
FOR (pl:Place)
REQUIRE pl.name IS UNIQUE;

// Event node constraints
// Note: For events with same name at different times, consider composite uniqueness
// Current implementation: simple name uniqueness
CREATE CONSTRAINT event_name_unique
IF NOT EXISTS
FOR (e:Event)
REQUIRE e.name IS UNIQUE;

// Event composite index for temporal queries
CREATE INDEX event_composite_idx
IF NOT EXISTS
FOR (e:Event)
ON (e.name, e.start_time);

// File node constraints
CREATE CONSTRAINT file_id_unique
IF NOT EXISTS
FOR (f:File)
REQUIRE f.file_id IS UNIQUE;

// File composite index for source-scoped queries
CREATE INDEX file_composite_idx
IF NOT EXISTS
FOR (f:File)
ON (f.file_id, f.source);

// === LEGACY ENTITY CONSTRAINTS (TO BE DEPRECATED) ===
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

// === CORE ENTITY PERFORMANCE INDEXES ===

// Extraction tier indexes for reprocessing queries
CREATE INDEX person_extraction_tier_idx
IF NOT EXISTS
FOR (p:Person)
ON (p.extraction_tier);

CREATE INDEX organization_extraction_tier_idx
IF NOT EXISTS
FOR (o:Organization)
ON (o.extraction_tier);

CREATE INDEX place_extraction_tier_idx
IF NOT EXISTS
FOR (pl:Place)
ON (pl.extraction_tier);

CREATE INDEX event_extraction_tier_idx
IF NOT EXISTS
FOR (e:Event)
ON (e.extraction_tier);

CREATE INDEX file_extraction_tier_idx
IF NOT EXISTS
FOR (f:File)
ON (f.extraction_tier);

// Extraction version indexes for reprocessing queries
CREATE INDEX person_extraction_version_idx
IF NOT EXISTS
FOR (p:Person)
ON (p.extractor_version);

CREATE INDEX organization_extraction_version_idx
IF NOT EXISTS
FOR (o:Organization)
ON (o.extractor_version);

CREATE INDEX place_extraction_version_idx
IF NOT EXISTS
FOR (pl:Place)
ON (pl.extractor_version);

CREATE INDEX event_extraction_version_idx
IF NOT EXISTS
FOR (e:Event)
ON (e.extractor_version);

CREATE INDEX file_extraction_version_idx
IF NOT EXISTS
FOR (f:File)
ON (f.extractor_version);

// Updated_at indexes for time-based queries
CREATE INDEX person_updated_at_idx
IF NOT EXISTS
FOR (p:Person)
ON (p.updated_at);

CREATE INDEX organization_updated_at_idx
IF NOT EXISTS
FOR (o:Organization)
ON (o.updated_at);

CREATE INDEX place_updated_at_idx
IF NOT EXISTS
FOR (pl:Place)
ON (pl.updated_at);

CREATE INDEX event_updated_at_idx
IF NOT EXISTS
FOR (e:Event)
ON (e.updated_at);

CREATE INDEX file_updated_at_idx
IF NOT EXISTS
FOR (f:File)
ON (f.updated_at);

// === LEGACY ENTITY PERFORMANCE INDEXES ===

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

// Expected output after Phase 1 implementation:
// === CORE ENTITIES (Phase 1) ===
// - 5 unique constraints (Person.email, Organization.name, Place.name, Event.name, File.file_id)
// - 2 composite indexes (Event: name+start_time, File: file_id+source)
// - 15 property indexes (5 entities × 3 fields: extraction_tier, extractor_version, updated_at)
//
// === LEGACY ENTITIES (Pre-refactor, to be deprecated) ===
// - 4 unique constraints (Service.name, Host.hostname, IP.addr, Proxy.name)
// - 1 composite index (Endpoint)
// - 11 property indexes (version, extraction_version, updated_at, confidence, host, chunk_id, doc_id)
// - 2 full-text indexes (Service, Host)
//
// === TOTAL ===
// - 9 unique constraints
// - 3 composite indexes
// - 26 property indexes
// - 3 relationship property indexes
// - 2 full-text indexes
