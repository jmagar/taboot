// Neo4j Schema Contract: LlamaCrawl v2
// Feature: 001-llamacrawl-v2-rag-platform
// Date: 2025-10-20
// Neo4j Version: 5.23+
// APOC Required: Yes

// ==============================================================================
// CONSTRAINTS (11 Total)
// ==============================================================================

// Document constraints
CREATE CONSTRAINT doc_docid IF NOT EXISTS
FOR (d:Document) REQUIRE d.docId IS UNIQUE;

CREATE CONSTRAINT doc_docid_not_null IF NOT EXISTS
FOR (d:Document) REQUIRE d.docId IS NOT NULL;

// Service constraints
CREATE CONSTRAINT service_name IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT service_name_not_null IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS NOT NULL;

// Host constraints
CREATE CONSTRAINT host_hostname IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS UNIQUE;

CREATE CONSTRAINT host_hostname_not_null IF NOT EXISTS
FOR (h:Host) REQUIRE h.hostname IS NOT NULL;

// IP constraints
CREATE CONSTRAINT ip_addr IF NOT EXISTS
FOR (i:IP) REQUIRE i.addr IS UNIQUE;

CREATE CONSTRAINT ip_addr_not_null IF NOT EXISTS
FOR (i:IP) REQUIRE i.addr IS NOT NULL;

// ReverseProxy constraints
CREATE CONSTRAINT proxy_name IF NOT EXISTS
FOR (p:ReverseProxy) REQUIRE p.name IS UNIQUE;

// Endpoint composite constraint
CREATE CONSTRAINT endpoint_uniq IF NOT EXISTS
FOR (e:Endpoint) REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE;

// Network constraints
CREATE CONSTRAINT network_cidr IF NOT EXISTS
FOR (n:Network) REQUIRE n.cidr IS UNIQUE;

// Container constraints
CREATE CONSTRAINT container_id IF NOT EXISTS
FOR (c:Container) REQUIRE c.containerId IS UNIQUE;

// Image constraints
CREATE CONSTRAINT image_id IF NOT EXISTS
FOR (i:Image) REQUIRE i.imageId IS UNIQUE;

// VPNTunnel constraints
CREATE CONSTRAINT vpn_id IF NOT EXISTS
FOR (v:VPNTunnel) REQUIRE v.tunnelId IS UNIQUE;

// TailscaleNode constraints
CREATE CONSTRAINT tailscale_nodeid IF NOT EXISTS
FOR (t:TailscaleNode) REQUIRE t.nodeId IS UNIQUE;


// ==============================================================================
// INDEXES (14 Total)
// ==============================================================================

// Document indexes
CREATE INDEX doc_url IF NOT EXISTS
FOR (d:Document) ON (d.url);

CREATE INDEX doc_source IF NOT EXISTS
FOR (d:Document) ON (d.sourceType);

CREATE INDEX doc_ingested IF NOT EXISTS
FOR (d:Document) ON (d.ingestedAt);

// Service indexes
CREATE INDEX service_proto_port IF NOT EXISTS
FOR (s:Service) ON (s.protocol, s.port);

CREATE INDEX service_created IF NOT EXISTS
FOR (s:Service) ON (s.createdAt);

// Host indexes
CREATE INDEX host_ip IF NOT EXISTS
FOR (h:Host) ON (h.ip);

CREATE INDEX host_os IF NOT EXISTS
FOR (h:Host) ON (h.osType);

// IP indexes
CREATE INDEX ip_public IF NOT EXISTS
FOR (i:IP) ON (i.isPublic);

// Endpoint indexes
CREATE INDEX endpoint_fqdn IF NOT EXISTS
FOR (e:Endpoint) ON (e.fqdn);

CREATE INDEX endpoint_auth IF NOT EXISTS
FOR (e:Endpoint) ON (e.authRequired);

// Container indexes
CREATE INDEX container_compose IF NOT EXISTS
FOR (c:Container) ON (c.composeProject, c.composeService);

CREATE INDEX container_image IF NOT EXISTS
FOR (c:Container) ON (c.image);

// TailscaleNode indexes
CREATE INDEX tailscale_ip IF NOT EXISTS
FOR (t:TailscaleNode) ON (t.tailscaleIp);

CREATE INDEX tailscale_lastseen IF NOT EXISTS
FOR (t:TailscaleNode) ON (t.lastSeen);


// ==============================================================================
// SAMPLE NODE CREATION (Idempotent MERGE Patterns)
// ==============================================================================

// -----------------------------
// Document Node
// -----------------------------
MERGE (d:Document {docId: $docId})
ON CREATE SET
  d.url = $url,
  d.title = $title,
  d.sourceType = $sourceType,
  d.ingestedAt = datetime(),
  d.updatedAt = datetime(),
  d.retentionPolicy = $retentionPolicy,
  d.contentHash = $contentHash,
  d.metadata = $metadata
ON MATCH SET
  d.updatedAt = datetime();

// Example parameters:
// {
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "url": "https://example.com/docs/api.md",
//   "title": "API Documentation",
//   "sourceType": "web",
//   "retentionPolicy": 90,
//   "contentHash": "a3b2c1d4e5f6...",
//   "metadata": {"author": "DevOps Team", "crawl_depth": 2}
// }

// -----------------------------
// Service Node
// -----------------------------
MERGE (s:Service {name: $name})
ON CREATE SET
  s.version = $version,
  s.protocol = $protocol,
  s.port = $port,
  s.description = $description,
  s.createdAt = datetime(),
  s.updatedAt = datetime(),
  s.schemaVersion = "2.0.0"
ON MATCH SET
  s.updatedAt = datetime(),
  s.version = coalesce($version, s.version),
  s.protocol = coalesce($protocol, s.protocol),
  s.port = coalesce($port, s.port);

// Example parameters:
// {
//   "name": "nginx",
//   "version": "1.25.3",
//   "protocol": "http",
//   "port": 80,
//   "description": "Web server and reverse proxy"
// }

// -----------------------------
// Host Node
// -----------------------------
MERGE (h:Host {hostname: $hostname})
ON CREATE SET
  h.ip = $ip,
  h.osType = $osType,
  h.description = $description,
  h.createdAt = datetime(),
  h.updatedAt = datetime()
ON MATCH SET
  h.updatedAt = datetime(),
  h.ip = coalesce($ip, h.ip),
  h.osType = coalesce($osType, h.osType);

// Example parameters:
// {
//   "hostname": "web01.example.com",
//   "ip": "192.168.1.10",
//   "osType": "linux",
//   "description": "Production web server"
// }

// -----------------------------
// IP Node
// -----------------------------
MERGE (i:IP {addr: $addr})
ON CREATE SET
  i.cidr = $cidr,
  i.isPublic = $isPublic,
  i.createdAt = datetime(),
  i.updatedAt = datetime()
ON MATCH SET
  i.updatedAt = datetime();

// Example parameters:
// {
//   "addr": "192.168.1.10",
//   "cidr": "192.168.1.0/24",
//   "isPublic": false
// }

// -----------------------------
// ReverseProxy Node
// -----------------------------
MERGE (p:ReverseProxy {name: $name})
ON CREATE SET
  p.type = $type,
  p.version = $version,
  p.configPath = $configPath,
  p.createdAt = datetime(),
  p.updatedAt = datetime()
ON MATCH SET
  p.updatedAt = datetime(),
  p.version = coalesce($version, p.version);

// Example parameters:
// {
//   "name": "traefik-main",
//   "type": "traefik",
//   "version": "2.10",
//   "configPath": "/etc/traefik/traefik.toml"
// }

// -----------------------------
// Endpoint Node
// -----------------------------
MERGE (e:Endpoint {
  scheme: $scheme,
  fqdn: $fqdn,
  port: $port,
  path: $path
})
ON CREATE SET
  e.method = $method,
  e.authRequired = $authRequired,
  e.createdAt = datetime(),
  e.updatedAt = datetime()
ON MATCH SET
  e.updatedAt = datetime(),
  e.authRequired = coalesce($authRequired, e.authRequired);

// Example parameters:
// {
//   "scheme": "https",
//   "fqdn": "api.example.com",
//   "port": 443,
//   "path": "/v1/users",
//   "method": "GET",
//   "authRequired": true
// }

// -----------------------------
// Network Node
// -----------------------------
MERGE (n:Network {cidr: $cidr})
ON CREATE SET
  n.name = $name,
  n.isPublic = $isPublic,
  n.description = $description,
  n.createdAt = datetime(),
  n.updatedAt = datetime()
ON MATCH SET
  n.updatedAt = datetime();

// Example parameters:
// {
//   "cidr": "10.0.0.0/24",
//   "name": "prod-vpc",
//   "isPublic": false,
//   "description": "Production VPC"
// }

// -----------------------------
// Container Node
// -----------------------------
MERGE (c:Container {containerId: $containerId})
ON CREATE SET
  c.name = $name,
  c.image = $image,
  c.composeProject = $composeProject,
  c.composeService = $composeService,
  c.createdAt = datetime(),
  c.updatedAt = datetime()
ON MATCH SET
  c.updatedAt = datetime();

// Example parameters:
// {
//   "containerId": "abc123def456",
//   "name": "taboot-api",
//   "image": "taboot/api:latest",
//   "composeProject": "taboot",
//   "composeService": "taboot-app"
// }

// -----------------------------
// Image Node
// -----------------------------
MERGE (i:Image {imageId: $imageId})
ON CREATE SET
  i.name = $name,
  i.registry = $registry,
  i.createdAt = datetime(),
  i.updatedAt = datetime()
ON MATCH SET
  i.updatedAt = datetime();

// Example parameters:
// {
//   "imageId": "sha256:a3b2c1d4e5f6...",
//   "name": "nginx:1.25",
//   "registry": "docker.io"
// }

// -----------------------------
// VPNTunnel Node
// -----------------------------
MERGE (v:VPNTunnel {tunnelId: $tunnelId})
ON CREATE SET
  v.name = $name,
  v.type = $type,
  v.localEndpoint = $localEndpoint,
  v.remoteEndpoint = $remoteEndpoint,
  v.createdAt = datetime(),
  v.updatedAt = datetime()
ON MATCH SET
  v.updatedAt = datetime();

// Example parameters:
// {
//   "tunnelId": "wg0",
//   "name": "site-to-site-vpn",
//   "type": "wireguard",
//   "localEndpoint": "10.0.1.1",
//   "remoteEndpoint": "10.0.2.1"
// }

// -----------------------------
// TailscaleNode Node
// -----------------------------
MERGE (t:TailscaleNode {nodeId: $nodeId})
ON CREATE SET
  t.name = $name,
  t.tailscaleIp = $tailscaleIp,
  t.machineKey = $machineKey,
  t.lastSeen = $lastSeen,
  t.createdAt = datetime(),
  t.updatedAt = datetime()
ON MATCH SET
  t.updatedAt = datetime(),
  t.lastSeen = coalesce($lastSeen, t.lastSeen);

// Example parameters:
// {
//   "nodeId": "ts_abc123",
//   "name": "server01",
//   "tailscaleIp": "100.64.1.10",
//   "machineKey": "encrypted_key_here",
//   "lastSeen": "2025-10-20T14:30:00Z"
// }


// ==============================================================================
// SAMPLE RELATIONSHIP CREATION (Idempotent MERGE with Provenance)
// ==============================================================================

// -----------------------------
// DEPENDS_ON Relationship
// -----------------------------
MATCH (s:Service {name: $serviceName})
MATCH (d:Service {name: $dependencyName})
MERGE (s)-[r:DEPENDS_ON]->(d)
ON CREATE SET
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.extractionMethod = $extractionMethod,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
  r.docId = coalesce($docId, r.docId);

// Example parameters:
// {
//   "serviceName": "nginx",
//   "dependencyName": "postgres",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.95,
//   "source": "tier_a",
//   "extractionMethod": "docker_compose_depends_on"
// }

// -----------------------------
// ROUTES_TO Relationship
// -----------------------------
MATCH (p:ReverseProxy {name: $proxyName})
MATCH (s:Service {name: $serviceName})
MERGE (p)-[r:ROUTES_TO]->(s)
ON CREATE SET
  r.host = $host,
  r.path = $path,
  r.tls = $tls,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.extractionMethod = $extractionMethod,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "proxyName": "traefik-main",
//   "serviceName": "nginx",
//   "host": "example.com",
//   "path": "/api",
//   "tls": true,
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.90,
//   "source": "tier_a",
//   "extractionMethod": "traefik_router_rule"
// }

// -----------------------------
// BINDS Relationship
// -----------------------------
MATCH (s:Service {name: $serviceName})
MATCH (h:Host {hostname: $hostname})
MERGE (s)-[r:BINDS]->(h)
ON CREATE SET
  r.port = $port,
  r.protocol = $protocol,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.extractionMethod = $extractionMethod,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "serviceName": "nginx",
//   "hostname": "web01.example.com",
//   "port": 80,
//   "protocol": "tcp",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.98,
//   "source": "tier_a",
//   "extractionMethod": "docker_compose_ports"
// }

// -----------------------------
// RUNS Relationship
// -----------------------------
MATCH (c:Container {containerId: $containerId})
MATCH (h:Host {hostname: $hostname})
MERGE (c)-[r:RUNS]->(h)
ON CREATE SET
  r.restartPolicy = $restartPolicy,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "containerId": "abc123def456",
//   "hostname": "docker-host01",
//   "restartPolicy": "always",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 1.0,
//   "source": "tier_a"
// }

// -----------------------------
// EXPOSES_ENDPOINT Relationship
// -----------------------------
MATCH (s:Service {name: $serviceName})
MATCH (e:Endpoint {
  scheme: $scheme,
  fqdn: $fqdn,
  port: $port,
  path: $path
})
MERGE (s)-[r:EXPOSES_ENDPOINT]->(e)
ON CREATE SET
  r.auth = $auth,
  r.rateLimit = $rateLimit,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.extractionMethod = $extractionMethod,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "serviceName": "api-gateway",
//   "scheme": "https",
//   "fqdn": "api.example.com",
//   "port": 443,
//   "path": "/v1/users",
//   "auth": "bearer",
//   "rateLimit": 1000,
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.92,
//   "source": "tier_b",
//   "extractionMethod": "spacy_endpoint_pattern"
// }

// -----------------------------
// CONNECTS_TO Relationship
// -----------------------------
MATCH (s1:Service {name: $sourceService})
MATCH (s2:Service {name: $targetService})
MERGE (s1)-[r:CONNECTS_TO]->(s2)
ON CREATE SET
  r.protocol = $protocol,
  r.encrypted = $encrypted,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "sourceService": "api-gateway",
//   "targetService": "postgres",
//   "protocol": "postgres",
//   "encrypted": true,
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.88,
//   "source": "tier_c"
// }

// -----------------------------
// RESOLVES_TO Relationship
// -----------------------------
MATCH (h:Host {hostname: $hostname})
MATCH (i:IP {addr: $ipAddr})
MERGE (h)-[r:RESOLVES_TO]->(i)
ON CREATE SET
  r.recordType = $recordType,
  r.ttl = $ttl,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "hostname": "web01.example.com",
//   "ipAddr": "192.168.1.10",
//   "recordType": "A",
//   "ttl": 300,
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 1.0,
//   "source": "tier_a"
// }

// -----------------------------
// RUNS_IN Relationship
// -----------------------------
MATCH (c:Container {containerId: $containerId})
MATCH (n:Network {cidr: $networkCidr})
MERGE (c)-[r:RUNS_IN]->(n)
ON CREATE SET
  r.networkMode = $networkMode,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "containerId": "abc123def456",
//   "networkCidr": "10.0.0.0/24",
//   "networkMode": "bridge",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 1.0,
//   "source": "tier_a"
// }

// -----------------------------
// BUILDS Relationship
// -----------------------------
MATCH (s:Service {name: $serviceName})
MATCH (i:Image {imageId: $imageId})
MERGE (s)-[r:BUILDS]->(i)
ON CREATE SET
  r.buildArgs = $buildArgs,
  r.dockerfile = $dockerfile,
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "serviceName": "api-gateway",
//   "imageId": "sha256:a3b2c1d4e5f6...",
//   "buildArgs": {"NODE_ENV": "production"},
//   "dockerfile": "./Dockerfile",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 1.0,
//   "source": "tier_a"
// }

// -----------------------------
// MENTIONS Relationship (Document to Chunk Metadata)
// -----------------------------
MATCH (d:Document {docId: $docId})
// Note: No MERGE on right side since chunks live in Qdrant
// This relationship stores metadata for traceability
CREATE (d)-[r:MENTIONS]->(metadata:ChunkMetadata {chunkId: $chunkId})
SET
  r.section = $section,
  r.span = $span,
  r.chunkHash = $chunkHash,
  r.chunkIndex = $chunkIndex,
  metadata.chunkId = $chunkId,
  metadata.text = $text,
  metadata.createdAt = datetime();

// Example parameters:
// {
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "chunkId": "550e8400-e29b-41d4-a716-446655440000:0",
//   "section": "Configuration",
//   "span": [120, 450],
//   "chunkHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
//   "chunkIndex": 0,
//   "text": "The nginx service listens on port 80..."
// }

// -----------------------------
// USES_VPN Relationship
// -----------------------------
MATCH (h:Host {hostname: $hostname})
MATCH (v:VPNTunnel {tunnelId: $tunnelId})
MERGE (h)-[r:USES_VPN]->(v)
ON CREATE SET
  r.docId = $docId,
  r.confidence = $confidence,
  r.source = $source,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END;

// Example parameters:
// {
//   "hostname": "remote-server01",
//   "tunnelId": "wg0",
//   "docId": "550e8400-e29b-41d4-a716-446655440000",
//   "confidence": 0.95,
//   "source": "tier_a"
// }


// ==============================================================================
// BATCH WRITE PATTERN (UNWIND for Bulk Inserts)
// ==============================================================================

// Example: Bulk insert Service nodes with DEPENDS_ON relationships
// Batch size: 2000 rows (optimal for deadlock avoidance)
UNWIND $batch AS row
MERGE (s:Service {name: row.serviceName})
ON CREATE SET
  s.version = row.version,
  s.protocol = row.protocol,
  s.port = row.port,
  s.createdAt = datetime(),
  s.updatedAt = datetime(),
  s.schemaVersion = "2.0.0"
ON MATCH SET
  s.updatedAt = datetime()
WITH s, row
MATCH (d:Service {name: row.dependencyName})
MERGE (s)-[r:DEPENDS_ON]->(d)
ON CREATE SET
  r.docId = row.docId,
  r.confidence = row.confidence,
  r.source = row.source,
  r.extractionMethod = row.extractionMethod,
  r.since = datetime()
ON MATCH SET
  r.confidence = CASE WHEN row.confidence > r.confidence THEN row.confidence ELSE r.confidence END;

// Example batch parameter:
// {
//   "batch": [
//     {
//       "serviceName": "nginx",
//       "version": "1.25",
//       "protocol": "http",
//       "port": 80,
//       "dependencyName": "postgres",
//       "docId": "550e8400-e29b-41d4-a716-446655440000",
//       "confidence": 0.95,
//       "source": "tier_a",
//       "extractionMethod": "docker_compose_depends_on"
//     },
//     // ... 1999 more rows
//   ]
// }


// ==============================================================================
// UTILITY QUERIES
// ==============================================================================

// Query: Count nodes by label
MATCH (n)
RETURN labels(n) AS label, count(n) AS count
ORDER BY count DESC;

// Query: Count relationships by type
MATCH ()-[r]->()
RETURN type(r) AS relType, count(r) AS count
ORDER BY count DESC;

// Query: Find orphan nodes (nodes with no relationships)
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) AS label, n.name AS name, count(*) AS orphanCount;

// Query: Verify provenance on all relationships
MATCH ()-[r]->()
WHERE r.docId IS NULL OR r.confidence IS NULL OR r.source IS NULL
RETURN type(r) AS missingProvenance, count(*) AS count;

// Query: Find duplicate relationships (should return 0)
MATCH (a)-[r1:DEPENDS_ON]->(b)
MATCH (a)-[r2:DEPENDS_ON]->(b)
WHERE id(r1) < id(r2)
RETURN a.name, b.name, count(*) AS duplicates;

// Query: Delete all data for a document (data governance)
MATCH (d:Document {docId: $docId})
OPTIONAL MATCH (d)-[r]-()
DELETE r, d;

// Example parameter:
// {
//   "docId": "550e8400-e29b-41d4-a716-446655440000"
// }

// Query: Find service dependencies (graph traversal)
MATCH path = (s:Service {name: $serviceName})-[:DEPENDS_ON*1..2]->(d:Service)
RETURN path;

// Example parameter:
// {
//   "serviceName": "nginx"
// }


// ==============================================================================
// VALIDATION QUERIES
// ==============================================================================

// Validate: All services have valid names (lowercase alphanumeric with hyphens/underscores)
MATCH (s:Service)
WHERE NOT s.name =~ '^[a-z0-9][a-z0-9_-]*$'
RETURN s.name AS invalidName;

// Validate: All endpoints have valid ports (1-65535)
MATCH (e:Endpoint)
WHERE e.port < 1 OR e.port > 65535
RETURN e.scheme, e.fqdn, e.port AS invalidPort;

// Validate: All relationships have confidence in [0.0, 1.0]
MATCH ()-[r]->()
WHERE r.confidence < 0.0 OR r.confidence > 1.0
RETURN type(r) AS relType, r.confidence AS invalidConfidence;

// Validate: All timestamps are in the past
MATCH (n)
WHERE n.createdAt > datetime()
RETURN labels(n) AS label, n.name AS name, n.createdAt AS futureTimestamp;


// ==============================================================================
// PERFORMANCE TUNING
// ==============================================================================

// Recommendation: Set transaction timeout for large batch writes
// In neo4j.conf:
// db.transaction.timeout=30s

// Recommendation: Enable parallel query execution
// In neo4j.conf:
// dbms.cypher.parallel_runtime_support=all

// Recommendation: Increase page cache for graph traversal
// In neo4j.conf:
// dbms.memory.pagecache.size=4g

// Recommendation: Increase heap size for large batch writes
// In neo4j.conf:
// dbms.memory.heap.initial_size=2g
// dbms.memory.heap.max_size=4g


// ==============================================================================
// END OF SCHEMA
// ==============================================================================

// Schema Version: 2.0.0
// Last Updated: 2025-10-20
// Constraints: 11
// Indexes: 14
// Node Types: 11
// Relationship Types: 11
