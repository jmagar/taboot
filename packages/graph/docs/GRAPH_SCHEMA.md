# Graph Schema (Neo4j)

This document defines the property graph used to store structured knowledge extracted from ingested content. It complements (but is distinct from) the extraction spec. The schema is opinionated toward homelab/infra sources (Docker Compose, SWAG, Unifi, Tailscale, GitHub, syslogs, API docs) and RAG use.

## Labels (Nodes)

* **Host**: physical/virtual machine.

  * Props: `id` (ULID), `hostname`, `ip`, `os`, `arch`, `env` (prod|lab|dev), `last_seen:datetime`.
  * Index: `hostname` unique; lookup index on `ip`.
* **Container**: containerized runtime unit.

  * Props: `id`, `name`, `image`, `tag`, `compose_service`, `compose_project`, `ports:list<int>`, `env:list<string>`, `last_seen`.
  * Index: composite on `(compose_project, compose_service)`.
* **Service**: logical networked service.

  * Props: `id`, `name`, `protocol` (http|tcp|udp|grpc), `port:int`, `path`, `version`, `last_seen`.
  * Index: `(name)` btree; `(protocol, port)`.
* **Endpoint**: externally reachable URL or socket.

  * Props: `id`, `scheme`, `host`, `port:int`, `path`, `fqdn`, `tls:bool`, `status:int?`, `last_checked`.
  * Index: unique on `(scheme, fqdn, port, path)`.
* **Network**: L2/L3 segment.

  * Props: `id`, `name`, `cidr`, `vlan:int?`.
  * Constraint: unique on `cidr`.
* **User**: human or service principal.

  * Props: `id`, `username`, `provider` (local|unifi|tailscale|github|oidc), `active:bool`.
  * Index: `(provider, username)`.
* **Credential**: API key or secret reference (metadata only).

  * Props: `id`, `kind` (token|key|password), `scope`, `rotates_after:date?`.
* **Repository**: code repo (GitHub, etc.).

  * Props: `id`, `platform`, `org`, `name`, `default_branch`, `visibility`.
  * Index: composite `(platform, org, name)` unique.
* **Package**: software component or image.

  * Props: `id`, `name`, `version`, `source` (pypi|npm|dockerhub|ghcr), `license?`.
* **Document**: ingested page or file.

  * Props: `id`, `doc_id`, `url`, `title`, `sha256`, `mime`, `lang`, `ingested_at:datetime`, `job_id`, `source` (web|github|api|syslog|config), `namespace`.
  * Index: `doc_id` unique; lookup index on `url`.
* **IP**: routable IP address.

  * Props: `id`, `addr` (string), `version:int` (4|6).
  * Constraint: unique on `addr`.

> Extend with domain-specific labels (e.g., `UnifiDevice`, `Tailnet`, `ReverseProxy`, `Domain`) as needed. Keep base constraints stable.

## Relationships

* `(:Host)-[:RUNS]->(:Container)` — container hosted on a machine.
* `(:Container)-[:EXPOSES]->(:Service)` — service exposed by a container.
* `(:Service)-[:BINDS_TO]->(:Endpoint)` — concrete endpoint mapping.
* `(:Endpoint)-[:RESOLVES_TO]->(:IP)` — DNS resolution.
* `(:Network)-[:CONTAINS]->(:Host)` — membership.
* `(:Service)-[:DEPENDS_ON]->(:Service)` — dependency graph.
* `(:ReverseProxy)-[:ROUTES_TO]->(:Service)` — SWAG/nginx routing.
* `(:User)-[:USES_CREDENTIAL]->(:Credential)` — secret usage (metadata only).
* `(:Repository)-[:BUILDS]->(:Package)` — CI/CD output.
* `(:Document)-[:MENTIONS]->(:Service|:Host|:Endpoint|:Package|:User|:Network)` — provenance links.
* `(:Package)-[:RUNS_IN]->(:Container)` — base image/package runtime.

Relationship properties: `since:datetime?`, `confidence:float 0..1`, `source` (extractor tier), `doc_id` for provenance.

## Constraints & Indexes (Cypher)

```cypher
// Hosts
CREATE CONSTRAINT host_hostname IF NOT EXISTS FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
CREATE INDEX host_ip IF NOT EXISTS FOR (h:Host) ON (h.ip);

// Containers
CREATE INDEX container_compose IF NOT EXISTS FOR (c:Container) ON (c.compose_project, c.compose_service);

// Services
CREATE INDEX service_name IF NOT EXISTS FOR (s:Service) ON (s.name);
CREATE INDEX service_proto_port IF NOT EXISTS FOR (s:Service) ON (s.protocol, s.port);

// Endpoints
CREATE CONSTRAINT endpoint_uniq IF NOT EXISTS FOR (e:Endpoint) REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE;

// Networks
CREATE CONSTRAINT network_cidr IF NOT EXISTS FOR (n:Network) REQUIRE n.cidr IS UNIQUE;

// Users
CREATE INDEX user_provider_username IF NOT EXISTS FOR (u:User) ON (u.provider, u.username);

// Documents
CREATE CONSTRAINT doc_docid IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
CREATE INDEX doc_url IF NOT EXISTS FOR (d:Document) ON (d.url);

// IPs
CREATE CONSTRAINT ip_addr IF NOT EXISTS FOR (i:IP) REQUIRE i.addr IS UNIQUE;
```

## Write Patterns (Upserts)

### Containers from Docker Compose

```cypher
UNWIND $containers AS row
MERGE (h:Host {hostname: row.host})
  ON CREATE SET h.id = row.host_ulid, h.last_seen = datetime()
  ON MATCH SET  h.last_seen = datetime()
MERGE (c:Container {name: row.name, compose_project: row.project, compose_service: row.service})
  ON CREATE SET c.id = row.id, c.image = row.image, c.tag = row.tag
MERGE (h)-[:RUNS]->(c)
WITH c, row
UNWIND row.ports AS p
MERGE (s:Service {name: row.service + ':' + toString(p.port), protocol: p.proto, port: p.port})
MERGE (c)-[:EXPOSES]->(s);
```

### Reverse Proxy Routes from SWAG

```cypher
UNWIND $routes AS r
MERGE (proxy:ReverseProxy {name: r.proxy_name})
MERGE (svc:Service {name: r.service, protocol: 'http', port: r.upstream_port})
MERGE (e:Endpoint {scheme: r.scheme, fqdn: r.host, port: coalesce(r.port, 443), path: coalesce(r.path, '/')})
MERGE (proxy)-[:ROUTES_TO {doc_id: r.doc_id, confidence: 0.9, source: 'TierA'}]->(svc)
MERGE (svc)-[:BINDS_TO]->(e);
```

### Provenance from Documents

```cypher
UNWIND $mentions AS m
MERGE (d:Document {doc_id: m.doc_id})
MERGE (t {id: m.target_id}) SET t:`${label}` // set label in your driver code
MERGE (d)-[:MENTIONS {source: m.tier, confidence: m.conf}]->(t);
```

## Read Patterns

* Services reachable on a host:

```cypher
MATCH (h:Host {hostname: $host})-[:RUNS]->(:Container)-[:EXPOSES]->(s:Service)
RETURN s ORDER BY s.port;
```

* External endpoints and upstreams:

```cypher
MATCH (e:Endpoint)-[:BINDS_TO]-(s:Service)
OPTIONAL MATCH (rp:ReverseProxy)-[:ROUTES_TO]->(s)
RETURN e, s, rp;
```

* Dependency subgraph with provenance:

```cypher
MATCH (a:Service {name: $svc})-[:DEPENDS_ON*1..3]->(b)
OPTIONAL MATCH (d:Document)-[m:MENTIONS]->(b)
RETURN a, b, collect({doc: d.doc_id, conf: m.confidence}) AS mentions;
```

## Mapping from Extraction Spec

Maintain a stable mapping table from extractor outputs to graph elements:

| Extracted type | Node label | Key fields                       | Relationships                 |
| -------------- | ---------- | -------------------------------- | ----------------------------- |
| host           | Host       | hostname, ip                     | CONTAINS, RUNS                |
| container      | Container  | compose_project, compose_service | RUNS, EXPOSES                 |
| service        | Service    | name or (protocol, port)         | EXPOSES, DEPENDS_ON, BINDS_TO |
| endpoint       | Endpoint   | scheme, fqdn, port, path         | BINDS_TO, RESOLVES_TO         |
| ip             | IP         | addr                             | RESOLVES_TO                   |
| user           | User       | provider, username               | USES_CREDENTIAL               |
| credential     | Credential | kind, scope                      | USES_CREDENTIAL               |
| package        | Package    | name, version                    | RUNS_IN                       |
| document       | Document   | doc_id                           | MENTIONS                      |

Document and relationship `doc_id` fields enable explainability and cleanup.
