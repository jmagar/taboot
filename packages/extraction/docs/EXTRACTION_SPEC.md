# Extraction Specification — Taboot v2 (October 2025)

A detailed design of the tiered extraction system responsible for converting ingested documentation and configurations into structured triples for the Neo4j property graph. This defines patterns, schemas, and operational guidance for deterministic, NLP-based, and LLM-based extraction tiers.

---

## 1. Purpose

The extraction layer transforms unstructured or semi-structured data (text, markdown, HTML, YAML, JSON, logs, configs) into machine-interpretable knowledge:

- **Entities** (Service, Host, Endpoint, Proxy, Network, Container, Image, Volume, VPNTunnel, etc.)
- **Relationships** (DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, CONNECTS_TO, MOUNTS_VOLUME, etc.)
- **Provenance metadata** for traceability and reprocessing.

It is decoupled from ingestion to avoid blocking large crawls and supports asynchronous reprocessing and benchmarking.

---

## 2. Entity Types

### Core Infrastructure Entities (11)

1. **Host** — Physical/virtual machine
   - Properties: `id` (ULID), `hostname`, `ip`, `os`, `arch`, `env` (prod|lab|dev), `lastSeen`
   - Constraints: Unique on `hostname`; index on `ip`

2. **Container** — Docker/runtime container
   - Properties: `id`, `name`, `image`, `tag`, `composeService`, `composeProject`, `ports`, `env`, `lastSeen`
   - Constraints: Composite index on `(composeProject, composeService)`

3. **Service** — Logical networked service
   - Properties: `id`, `name`, `protocol` (http|tcp|udp|grpc), `port`, `path`, `version`, `lastSeen`
   - Constraints: Unique on `name`; index on `(protocol, port)`

4. **Endpoint** — Externally reachable URL or socket
   - Properties: `id`, `scheme`, `host`, `port`, `path`, `fqdn`, `tls`, `status`, `lastChecked`
   - Constraints: Unique on `(scheme, fqdn, port, path)`

5. **Network** — L2/L3 network segment
   - Properties: `id`, `name`, `cidr`, `vlan`
   - Constraints: Unique on `cidr`

6. **IP** — Routable IP address
   - Properties: `id`, `addr`, `version` (4|6)
   - Constraints: Unique on `addr`

7. **User** — Human or service principal
   - Properties: `id`, `username`, `provider` (local|unifi|tailscale|github|oidc), `active`
   - Constraints: Index on `(provider, username)`

8. **Credential** — API key or secret reference
   - Properties: `id`, `kind` (token|key|password), `scope`, `rotatesAfter`

9. **Repository** — Code repository (GitHub, etc.)
   - Properties: `id`, `platform`, `org`, `name`, `defaultBranch`, `visibility`
   - Constraints: Unique on `(platform, org, name)`

10. **Package** — Software component or image
    - Properties: `id`, `name`, `version`, `source` (pypi|npm|dockerhub|ghcr), `license`

11. **Document** — Ingested page or file
    - Properties: `id`, `docId`, `url`, `title`, `sha256`, `mime`, `lang`, `ingestedAt`, `jobId`, `source`, `namespace`
    - Constraints: Unique on `docId`; index on `url`

### Extended Infrastructure Entities (15)

12. **ReverseProxy** — Reverse proxy/router instance
    - Properties: `id`, `name`, `type` (nginx|traefik|haproxy|swag), `version`, `configPath`

13. **VirtualHost** — Virtual server configuration
    - Properties: `id`, `serverName`, `listenPort`, `protocol`, `sslEnabled`

14. **Route** — Routing rule configuration
    - Properties: `id`, `name`, `matcherType`, `pattern`, `priority`, `methods[]`

15. **Upstream** — Load balancer pool
    - Properties: `id`, `name`, `algorithm` (round-robin|least-conn|ip-hash), `healthCheckConfig`

16. **Backend** — Individual backend instance
    - Properties: `id`, `host`, `port`, `protocol`, `weight`, `maxFails`

17. **Image** — Container image
    - Properties: `id`, `name`, `tag`, `digest`, `size`, `created`, `author`, `architecture`, `os`

18. **ImageLayer** — Container image layer
    - Properties: `id`, `digest`, `size`, `mediaType`, `command`

19. **Volume** — Storage volume
    - Properties: `id`, `name`, `driver`, `mountPath`

20. **Interface** — Network interface (physical/virtual)
    - Properties: `id`, `name`, `macAddress`, `type`, `mtu`, `speed`, `enabled`, `adminStatus`, `operStatus`

21. **VLAN** — IEEE 802.1Q virtual LAN
    - Properties: `id`, `vlanId`, `name`, `siteId`, `status`

22. **Switch** — Layer 2/3 switching device
    - Properties: `id`, `hostname`, `model`, `mgmtIp`, `osVersion`, `serialNumber`

23. **Router** — Layer 3 routing device
    - Properties: `id`, `hostname`, `model`, `mgmtIp`, `osVersion`, `bgpAsn`

24. **Gateway** — Network gateway device
    - Properties: `id`, `hostname`, `model`, `wanCount`, `lanCount`

25. **AccessPoint** — Wireless access point
    - Properties: `id`, `mac`, `model`, `radioCount`, `siteId`

26. **VPNTunnel** — VPN tunnel (IPsec/WireGuard/etc.)
    - Properties: `id`, `name`, `type`, `status`, `encryption`, `peerLocal`, `peerRemote`

### Tailscale-Specific Entities (2)

27. **TailscaleNode** — Device in Tailscale mesh
    - Properties: `id`, `hostname`, `tailscaleIp`, `publicKey`, `os`, `online`, `lastSeen`

28. **Tailnet** — Tailscale private network
    - Properties: `id`, `domain`, `owner`, `aclPolicy`

### UniFi-Specific Entities (3)

29. **UnifiSite** — UniFi Controller site
    - Properties: `id`, `siteId`, `name`, `description`

30. **UnifiDevice** — UniFi network device
    - Properties: `id`, `mac`, `type` (uap|usw|ugw), `model`, `adopted`, `state`

31. **UnifiClient** — Connected client
    - Properties: `id`, `mac`, `hostname`, `ip`, `connectionType`

### DNS and Discovery Entities (3)

32. **DNSZone** — DNS zone
    - Properties: `id`, `zoneName`, `type` (master|slave), `serial`, `ttl`

33. **DNSRecord** — DNS resource record
    - Properties: `id`, `name`, `type` (A|AAAA|CNAME|MX|TXT|SRV), `value`, `ttl`

34. **ConsulService** — Consul-registered service
    - Properties: `id`, `serviceId`, `serviceName`, `address`, `port`, `tags[]`

---

## 3. Relationship Types

### Core Infrastructure Relationships (11)

1. **RUNS** — `(:Host)-[:RUNS]->(:Container)`
   - Container hosted on machine

2. **EXPOSES** — `(:Container)-[:EXPOSES]->(:Service)`
   - Service exposed by container

3. **BINDS_TO** — `(:Service)-[:BINDS_TO]->(:Endpoint)`
   - Concrete endpoint mapping

4. **RESOLVES_TO** — `(:Endpoint)-[:RESOLVES_TO]->(:IP)`
   - DNS resolution

5. **CONTAINS** — `(:Network)-[:CONTAINS]->(:Host)`
   - Network membership

6. **DEPENDS_ON** — `(:Service)-[:DEPENDS_ON]->(:Service)`
   - Service dependency graph
   - Properties: `since`, `confidence`, `source`, `docId`

7. **ROUTES_TO** — `(:ReverseProxy)-[:ROUTES_TO]->(:Service)`
   - SWAG/nginx routing
   - Properties: `host`, `path`, `tls`, `docId`, `confidence`, `source`

8. **USES_CREDENTIAL** — `(:User)-[:USES_CREDENTIAL]->(:Credential)`
   - Secret usage (metadata only)

9. **BUILDS** — `(:Repository)-[:BUILDS]->(:Package)`
   - CI/CD output

10. **MENTIONS** — `(:Document)-[:MENTIONS]->(:Service|Host|Endpoint|Package|User|Network)`
    - Provenance links from documents to entities
    - Properties: `section`, `hash`, `span`, `confidence`, `source` (extractor tier), `docId`

11. **RUNS_IN** — `(:Package)-[:RUNS_IN]->(:Container)`
    - Base image/package runtime

### Extended Infrastructure Relationships (17)

12. **CONNECTS_TO** — `(:Container|Interface)-[:CONNECTS_TO]->(:Network)`
    - Network connectivity
    - Properties: `ipAddress`, `aliases[]`, `gateway`

13. **MOUNTS_VOLUME** — `(:Service|Container)-[:MOUNTS_VOLUME]->(:Volume)`
    - Volume mounting
    - Properties: `type`, `source`, `target`, `readOnly`

14. **EXTENDS** — `(:Service)-[:EXTENDS]->(:Service)`
    - Docker Compose service inheritance
    - Properties: `file`, `service`

15. **BASED_ON** — `(:Container)-[:BASED_ON]->(:Image)`
    - Container runtime image reference

16. **CONSISTS_OF** — `(:Image)-[:CONSISTS_OF]->(:ImageLayer)`
    - Image layer composition
    - Properties: `order` (0 = base)

17. **CONTAINS_PACKAGE** — `(:Image|ImageLayer)-[:CONTAINS_PACKAGE]->(:Package)`
    - SBOM software composition
    - Properties: `installedBy` (layer digest)

18. **HAS_INTERFACE** — `(:Host|Switch|Router)-[:HAS_INTERFACE]->(:Interface)`
    - Interface ownership
    - Properties: `slot`, `port`

19. **ASSIGNED_TO** — `(:IP)-[:ASSIGNED_TO]->(:Interface)`
    - IP assignment
    - Properties: `isPrimary`, `family` (ipv4|ipv6)

20. **BELONGS_TO_VLAN** — `(:Network|Interface)-[:BELONGS_TO_VLAN]->(:VLAN)`
    - VLAN association
    - Properties: `tagged`, `native`

21. **TRUNK_LINK** — `(:Interface)-[:TRUNK_LINK]->(:Interface)`
    - Trunk connection
    - Properties: `allowedVlans[]`, `nativeVlanId`, `encapsulation`

22. **ADJACENT_TO** — `(:Device)-[:ADJACENT_TO]->(:Device)`
    - L2 neighbor adjacency
    - Properties: `discoveredBy` (CDP|LLDP), `localPort`, `remotePort`

23. **HAS_VIRTUAL_HOST** — `(:ReverseProxy)-[:HAS_VIRTUAL_HOST]->(:VirtualHost)`
    - Virtual host configuration
    - Properties: `priority`

24. **HAS_ROUTE** — `(:VirtualHost)-[:HAS_ROUTE]->(:Route)`
    - Routing rules
    - Properties: `order`

25. **USES_UPSTREAM** — `(:Route)-[:USES_UPSTREAM]->(:Upstream)`
    - Load balancer pool reference

26. **DISTRIBUTES_TO** — `(:Upstream)-[:DISTRIBUTES_TO]->(:Backend)`
    - Backend server in pool
    - Properties: `weight`, `active`

27. **PEERS_WITH** — `(:TailscaleNode)-[:PEERS_WITH]->(:TailscaleNode)`
    - Tailscale mesh peering
    - Properties: `connectionType` (direct|relay), `derpRegion`, `latency`

28. **MEMBER_OF** — `(:TailscaleNode|UnifiDevice)-[:MEMBER_OF]->(:Tailnet|UnifiSite)`
    - Membership relationships
    - Properties: `joinedAt`

### Provenance Relationships (3)

29. **DERIVED_FROM** — `(:Entity)-[:DERIVED_FROM]->(:Source)`
    - Data origin tracking

30. **ATTRIBUTED_TO** — `(:Entity)-[:ATTRIBUTED_TO]->(:Agent)`
    - Responsibility attribution

31. **GENERATED_BY** — `(:Entity)-[:GENERATED_BY]->(:Activity)`
    - Creation activity tracking

### Universal Relationship Properties

All relationships support these optional properties:

- `since` (datetime) — When relationship first observed
- `confidence` (float 0..1) — Extraction confidence score
- `source` (string) — Extractor tier (TierA, TierB, TierC)
- `docId` (string) — Source document for provenance
- `extractionMethod` (string) — Specific method (regex|spacy|llm)
- `schemaVersion` (string) — Schema version when created

---

## 4. Extraction Tiers

### Tier A — Deterministic (Rule-Based)

**Objective:** Fast, low-cost parsing of structured patterns in configs and documentation.

**Techniques:**

- Regex + YAML/JSON parsers.
- **Aho-Corasick dictionary matching** for known services (3-4M chars in 1-1.3s).
- Link graph and fenced code parsing.
- IP/hostname/port pattern matching.

**Service Dictionary (Aho-Corasick):**
```
nginx, traefik, haproxy, caddy, swag
postgres, mysql, mariadb, redis, mongodb, elasticsearch, neo4j, qdrant
portainer, grafana, prometheus, loki
plex, sonarr, radarr, overseerr, tautulli
homeassistant, pihole, unifi-controller
ollama, firecrawl
...
```

**Outputs:**

- Direct edges: `(:Service)-[:BINDS]->(:IP)`, `(:Proxy)-[:ROUTES_TO]->(:Service)`
- Placeholder edges for resolution: e.g., unknown container names, missing IPs.

**Docker Compose Parsing (Cypher Output):**
```cypher
UNWIND $containers AS row
MERGE (h:Host {hostname: row.host})
  ON CREATE SET h.id = row.hostUlid, h.lastSeen = datetime()
  ON MATCH SET h.lastSeen = datetime()
MERGE (c:Container {name: row.name, composeProject: row.project, composeService: row.service})
  ON CREATE SET c.id = row.id, c.image = row.image, c.tag = row.tag
MERGE (h)-[:RUNS]->(c)
WITH c, row
UNWIND row.ports AS p
MERGE (s:Service {name: row.service + ':' + toString(p.port), protocol: p.proto, port: p.port})
MERGE (c)-[:EXPOSES]->(s)
```

**Performance Target:** ≥50 pages/sec (CPU)

---

### Tier B — NLP (spaCy)

**Objective:** Capture grammatical relations and entity co-occurrences missed by deterministic rules.

**Base Model:** `en_core_web_md` (balanced)
**Alternative:** `en_core_web_trf` (higher accuracy, slower)

**Pipeline Components:**

1. **EntityRuler** — Domain-specific patterns
   ```python
   # Services (exact + patterns)
   {"label": "SERVICE", "pattern": "nginx"}
   {"label": "SERVICE", "pattern": [{"TEXT": {"REGEX": r"^[a-z][a-z0-9]*_\d+$"}}]}

   # IPs
   {"label": "IP", "pattern": [{"TEXT": {"REGEX": r"^(?:25[0-5]|...)\.(?:...){{3}}$"}}]}

   # Hostnames
   {"label": "HOST", "pattern": [{"TEXT": {"REGEX": r"^[a-z0-9][a-z0-9-]*\.[a-z]{2,}$"}}]}

   # Ports
   {"label": "PORT", "pattern": [{"TEXT": {"REGEX": r"^(?:[1-9]\d{0,3}|...)$"}}]}

   # Endpoints
   {"label": "ENDPOINT", "pattern": [{"TEXT": {"REGEX": r"^/(?:[a-z0-9_-]+/?)+$"}}]}
   ```

2. **DependencyMatcher** — Relationship extraction
   ```python
   # "nginx depends on postgres"
   [
       {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"LEMMA": {"IN": ["depend", "require", "need"]}}},
       {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subject",
        "RIGHT_ATTRS": {"DEP": "nsubj", "ENT_TYPE": "SERVICE"}},
       {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "prep",
        "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}},
       {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "object",
        "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "SERVICE"}}
   ]
   ```

3. **SentenceClassifier** — Filter technical vs. noise sentences

**Relationship Verbs:**
- **DEPENDS_ON:** depend, require, need, connect, link, communicate
- **ROUTES_TO:** route, proxy, forward, redirect
- **BINDS:** bind, listen, expose
- **EXPOSES_ENDPOINT:** expose, provide, serve

**Performance Target:** ≥200 sentences/sec (md), ≥40 sentences/sec (trf)

---

### Tier C — LLM Windows (Qwen3-4B-Instruct)

**Objective:** Resolve ambiguous spans and extract nuanced relationships.

**Runtime:** Qwen3-4B-Instruct via Ollama (GPU-quantized inference)

**Window Policy:**
- Input window ≤512 tokens (2–4 sentences)
- Batching: 8–16 windows per request
- Cache: SHA-256(window + extractorVersion) in Redis (TTL: 7 days)

**Output Schema:**
```json
{
  "entities": [
    {"type": "Service|Host|IP|ReverseProxy|Endpoint|Network|Container|Image|Volume|VPNTunnel|TailscaleNode",
     "name": "...",
     "props": {"version": "...", "port": 8080}}
  ],
  "relations": [
    {"type": "DEPENDS_ON|ROUTES_TO|BINDS|RUNS|EXPOSES_ENDPOINT|CONNECTS_TO|MOUNTS_VOLUME|BASED_ON|PEERS_WITH",
     "src": "...", "dst": "...", "props": {"host": "...", "path": "/"}}
  ],
  "provenance": {"docId": "...", "section": "...", "span": [start, end]}
}
```

**Few-Shot Prompting (3-5 examples per entity type):**
```
Example 1:
Input: "Traefik routes traffic to the backend API running on api.internal:8080"
Output: {
  "entities": [
    {"type": "ReverseProxy", "name": "traefik"},
    {"type": "Service", "name": "backend-api", "props": {"port": 8080}},
    {"type": "Host", "name": "api.internal"}
  ],
  "relations": [
    {"type": "ROUTES_TO", "src": "traefik", "dst": "backend-api", "props": {"host": "api.internal", "port": 8080}}
  ]
}
```

**Confidence Scoring:**
- Use token-level logprobs if available (most accurate signal)
- Aggregate token probabilities for entity/relationship confidence
- Filter extraction if confidence < 0.70; re-extract if 0.70-0.80

**Decoding:**
- Temperature 0.0, top_p 0.0
- Stop on `\n\n`
- Post-validate with Pydantic schema
- Reject and requeue malformed JSON

**Performance Target:** Median ≤250ms/window, P95 ≤750ms

---

## 5. Entity Resolution and Canonicalization

### Canonical Keys

**Service Names:**
- Normalize: lowercase, slug format
- Merge aliases: nginx → Nginx → NGINX

**Hostnames:**
- Store FQDN and short name
- Lowercase normalization
- Remove trailing dots

**IP Addresses:**
- IPv4: Dotted decimal (192.168.1.1)
- IPv6: Compressed format (2001:db8::1)

**Container/Image Names:**
- Registry normalization (docker.io implicit)
- Tag defaulting (latest implicit)

### Cross-Reference Strategy

**Deterministic Sources (Tier A):**
- Docker Compose
- SWAG configs
- Tailscale API
- UniFi Controller API

**Graph-Based Resolution:**
- Merge nodes with same `Service.name` (case-insensitive)
- Link `Host.hostname` ↔ `IP.addr` co-occurrence
- Use `ADJACENT_TO` relationships for device identity

### Stub Nodes for Unresolved References

```cypher
MERGE (s:Service {name: $referenced_service})
ON CREATE SET s.status = 'unresolved', s.firstMentioned = datetime()
```

---

## 6. Graph Schema Constraints

### Neo4j Constraints

```cypher
-- Hosts
CREATE CONSTRAINT host_hostname IF NOT EXISTS FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
CREATE INDEX host_ip IF NOT EXISTS FOR (h:Host) ON (h.ip);

-- Containers
CREATE INDEX container_compose IF NOT EXISTS FOR (c:Container) ON (c.composeProject, c.composeService);

-- Services
CREATE INDEX service_name IF NOT EXISTS FOR (s:Service) ON (s.name);
CREATE INDEX service_proto_port IF NOT EXISTS FOR (s:Service) ON (s.protocol, s.port);

-- Endpoints
CREATE CONSTRAINT endpoint_uniq IF NOT EXISTS FOR (e:Endpoint) REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE;

-- Networks
CREATE CONSTRAINT network_cidr IF NOT EXISTS FOR (n:Network) REQUIRE n.cidr IS UNIQUE;

-- IPs
CREATE CONSTRAINT ip_addr IF NOT EXISTS FOR (i:IP) REQUIRE i.addr IS UNIQUE;

-- Documents
CREATE CONSTRAINT doc_docid IF NOT EXISTS FOR (d:Document) REQUIRE d.docId IS UNIQUE;
CREATE INDEX doc_url IF NOT EXISTS FOR (d:Document) ON (d.url);
```

### Schema Versioning

All nodes track schema version:
```cypher
MATCH (n)
WHERE NOT EXISTS(n.schemaVersion)
SET n.schemaVersion = "1.0.0", n.updatedAt = datetime()
```

---

## 7. Batch Writing and Performance

### UNWIND Batch Pattern

**Batch Size:** 1–5k triples per UNWIND
**Target Throughput:** ≥20k edges/min

```cypher
UNWIND $batch AS row
MATCH (s:Service {name: row.service})
MATCH (h:Host {hostname: row.host})
MERGE (s)-[r:RUNS_ON]->(h)
SET r.port = row.port,
    r.protocol = row.protocol,
    r.confidence = row.confidence,
    r.source = row.source,
    r.docId = row.docId
```

### Idempotent Operations

```cypher
MERGE (s:Service {name: $name})
ON CREATE SET s.id = randomUUID(), s.createdAt = datetime()
ON MATCH SET s.updatedAt = datetime()
```

---

## 8. Validation and Quality Metrics

### Test Fixtures

~300 labeled windows:
- Docker Compose samples
- SWAG proxy configs
- Technical README excerpts
- API documentation snippets

### Quality Metrics

- **Entity-Level F1:** Full entity must match
- **Token-Level F1:** Partial matches allowed
- **Relationship Precision/Recall:** Per relationship type
- **Provenance Accuracy:** % extractions traceable to source span
- **Confidence Distribution:** Histogram of scores

### CI Guardrails

- Fail if F1 drops ≥2 points
- Fail if entity-level precision < 0.80
- Fail if provenance accuracy < 0.90

---

## 9. Performance Optimizations

### Tier A Optimizations

1. **Aho-Corasick:** Build automaton once, reuse for all docs
2. **Batch Processing:** Process 100-500 docs in parallel
3. **Lazy Loading:** Parse YAML/JSON on-demand

### Tier B Optimizations

1. **Batch Processing:** Use `nlp.pipe()` for efficiency
2. **Model Selection:**
   - `md`: 200-280 sent/sec (balanced)
   - `trf`: 40-60 sent/sec (accuracy)
3. **Component Pruning:** Disable unused components

### Tier C Optimizations

1. **Batching:** 8-16 windows per request
2. **Caching:** Redis hit rate target ≥70%
3. **Confidence Filtering:** Skip low-confidence (< 0.70) extractions

---

## 10. Dead Letter Queue (DLQ)

### Redis Key Patterns

```
dlq:extraction:{content_hash} → Failed extraction
dlq:retry:{content_hash} → Retry count
dlq:failed:{content_hash} → Permanently failed (max retries exceeded)
```

### Retry Strategy

- Max 3 retries
- Exponential backoff: 1s, 5s, 25s
- 30-day retention for analysis

---

## 11. Monitoring and Observability

### Metrics to Track

- **Throughput:** Pages/sec (A), Sentences/sec (B), Windows/sec (C)
- **Latency:** p50, p95, p99 per tier
- **Quality:** Tier hit ratios, confidence scores, F1 per type
- **Cache:** Redis hit rate, eviction rate, DLQ size
- **Graph:** Edges written/min, batch write latency

### Tracing Chain

```
docId → section → windows → triples → Neo4j txId
```

---

## 12. Versioning & Validation

- Every extractor version stamped in output: `extractorVersion = semver`
- Regression suite: labeled windows → precision/recall/F1 guardrails
- CI fails if F1 drops ≥2 pts vs. baseline
- Unit tests for regex, spaCy matchers, LLM validation

---

## 13. Roadmap

1. ✓ Architecture designed
2. Implement deterministic extractors (Tier A)
3. Integrate spaCy with EntityRuler patterns (Tier B)
4. Connect Ollama Qwen3-4B for Tier C micro-windows
5. Build entity resolution layer with Docker/Unifi/Tailscale APIs
6. Add batch write queue to Neo4j
7. Set up Prometheus/Grafana monitoring
8. Train relation classifier to optimize LLM calls

---

**Document Version:** 2.0.0
**Last Updated:** 2025-01-20
**Schema Version:** 2.0.0
**Author:** Jacob Magar
**License:** Proprietary
