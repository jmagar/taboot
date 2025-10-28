# Neo4j Graph Architecture Refactor

**Status**: Planning Phase
**Target**: Core + Extended Extraction (NO AST, NO Enrichment)
**Approach**: Full rewrite with no backwards compatibility
**Development Method**: TDD (Red-Green-Refactor)
**Max Parallel Agents**: 10

---

## Executive Summary

Refactor Taboot's graph architecture from domain-specific entities (Service, Host, IP) to a flexible core + reader-specific model inspired by CORE's architecture. This enables multi-source RAG with proper temporal tracking, relationship validation, and infrastructure correlation.

**Key Changes:**
- 5 core entities (Person, Organization, Place, Event, File)
- 58 reader-specific entities across 10 sources
- Temporal tracking on ALL nodes and relationships
- Pydantic schemas for ALL relationships
- Separate entities for properties (env vars, headers, rules) for maximum queryability

**Timeline Estimate**: 50-60 hours with aggressive parallelization

---

## Complete Entity Inventory (63 Total)

### Core Entities (5)

1. **Person** - Individual people
   - Properties: name, email, role, bio, github_username, reddit_username, youtube_channel
   - Sources: GitHub users, Gmail contacts, Reddit users, YouTube creators

2. **Organization** - Companies, teams, groups
   - Properties: name, industry, size, website, description
   - Sources: GitHub orgs, Gmail domains, Subreddit communities, YouTube channels

3. **Place** - Physical or virtual locations
   - Properties: name, address, coordinates, place_type
   - Sources: Tailscale networks, Unifi sites, Gmail locations

4. **Event** - Time-based occurrences
   - Properties: name, start_time, end_time, location, event_type
   - Sources: Gmail meetings, GitHub releases, commit events, Google Calendar events

5. **File** - Documents, code, media
   - Properties: name, file_id, source, mime_type, size_bytes, url
   - Sources: GitHub files, Gmail attachments, YouTube transcripts

### Docker Compose Reader (12)

6. **ComposeFile** (root entity)
   - file_path, version, project_name

7. **ComposeProject**
   - name, version, file_path

8. **ComposeService**
   - name, image, command, entrypoint, restart, cpus, memory, user, working_dir, hostname

9. **ComposeNetwork**
   - name, driver, external, enable_ipv6, ipam_driver, ipam_config

10. **ComposeVolume**
    - name, driver, external, driver_opts

11. **PortBinding** (separate entity)
    - host_ip, host_port, container_port, protocol

12. **EnvironmentVariable** (separate entity)
    - key, value, service_name

13. **ServiceDependency** (separate entity)
    - source_service, target_service, condition (service_started, service_healthy)

14. **ImageDetails** (separate entity)
    - image_name, tag, registry, digest

15. **HealthCheck** (separate entity)
    - test, interval, timeout, retries, start_period

16. **BuildContext** (separate entity)
    - context_path, dockerfile, target, args

17. **DeviceMapping** (separate entity)
    - host_device, container_device, permissions

### SWAG Reader (6)

18. **SwagConfigFile** (root entity)
    - file_path, version, parsed_at

19. **Proxy**
    - name, proxy_type, config_path

20. **ProxyRoute** (replaces old concept)
    - server_name, upstream_app, upstream_port, upstream_proto, tls_enabled

21. **LocationBlock** (separate entity)
    - path, proxy_pass_url, auth_enabled, auth_type

22. **UpstreamConfig** (separate entity)
    - app (IP/hostname), port, proto (http/https)

23. **ProxyHeader** (separate entity)
    - header_name, header_value, header_type (add_header, proxy_set_header)

### GitHub Reader (12)

24. **Repository**
    - owner, name, full_name, url, default_branch, description, language, stars, forks, open_issues, is_private, is_fork

25. **Issue**
    - number, title, state, body, author_login, created_at, closed_at, comments_count

26. **PullRequest**
    - number, title, state, base_branch, head_branch, merged, merged_at, commits, additions, deletions

27. **Commit**
    - sha, message, author_login, author_name, author_email, timestamp, tree_sha, parent_shas, additions, deletions

28. **Branch**
    - name, protected, sha, ref

29. **Tag**
    - name, sha, ref, message, tagger

30. **GitHubLabel**
    - name, color, description

31. **Milestone**
    - number, title, state, due_on, description

32. **Comment**
    - id, author_login, body, created_at, updated_at

33. **Release**
    - tag_name, name, body, draft, prerelease, created_at, published_at, tarball_url, zipball_url

34. **Documentation** (separate from File)
    - file_path, content, format (markdown, rst, txt), title

35. **BinaryAsset**
    - file_path, size, mime_type, download_url

### Gmail Reader (4)

36. **Email**
    - message_id, thread_id, subject, snippet, body, sent_at, labels, size_estimate, has_attachments, in_reply_to, references

37. **Thread**
    - thread_id, subject, message_count, participant_count, first_message_at, last_message_at, labels

38. **GmailLabel**
    - label_id, name, type (system, user), color, message_count

39. **Attachment**
    - attachment_id, filename, mime_type, size, content_hash, is_inline

### Reddit Reader (3)

40. **Subreddit**
    - name, display_name, description, subscribers, created_utc, over_18

41. **RedditPost**
    - post_id, title, selftext, score, num_comments, created_utc, url, permalink, is_self, over_18, gilded

42. **RedditComment**
    - comment_id, body, score, created_utc, permalink, parent_id, depth, gilded, edited

### YouTube Reader (3)

43. **Video**
    - video_id, title, url, duration, views, published_at, description, language

44. **Channel**
    - channel_id, channel_name, channel_url, subscribers, verified

45. **Transcript**
    - transcript_id, video_id, language, auto_generated, content

### Tailscale Reader (3)

46. **TailscaleDevice**
    - device_id, hostname, os, ipv4_address, ipv6_address, endpoints, key_expiry, is_exit_node, subnet_routes, ssh_enabled, tailnet_dns_name

47. **TailscaleNetwork**
    - network_id, name, cidr, global_nameservers, search_domains

48. **TailscaleACL**
    - rule_id, action, source_tags, destination_tags, ports

### Unifi Reader (9)

49. **UnifiDevice**
    - mac, hostname, type, model, adopted, state, ip, firmware_version, link_speed, connection_type, uptime

50. **UnifiClient**
    - mac, hostname, ip, network, is_wired, link_speed, connection_type, uptime

51. **UnifiNetwork**
    - network_id, name, vlan_id, subnet, gateway_ip, dns_servers, wifi_name

52. **UnifiSite**
    - site_id, name, description, wan_ip, gateway_ip, dns_servers

53. **PortForwardingRule** (✅ Full Support)
    - rule_id, name, enabled, proto (tcp/udp/tcp_udp), src, dst_port, fwd (internal IP), fwd_port, pfwd_interface
    - API: `/api/s/{site}/rest/portforward`

54. **FirewallRule** (✅ Full Support)
    - rule_id, name, enabled, action (ALLOW/DROP/REJECT), protocol, ip_version, index (priority), source_zone, dest_zone, logging
    - API: `/v2/api/site/{site}/firewall-policies` (requires UniFi Network Application 7.0+)

55. **NATRule** (⚠️ Partial Support - DNAT only)
    - DNAT available via PortForwardingRule
    - SNAT/Masquerade not exposed via API
    - Phase 2 implementation

56. **TrafficRule** (✅ Full Support - QoS/Traffic Shaping)
    - rule_id, name, enabled, action, bandwidth_limit (download_kbps, upload_kbps), matching_target, ip_addresses, domains, schedule
    - API: `/v2/api/site/{site}/trafficrules` (requires UniFi Network Application 7.0+)

57. **TrafficRoute** (⚠️ Partial Support - Static Routes)
    - route_id, name, enabled, next_hop (gateway), matching_target, network_id, ip_addresses, domains
    - API: `/v2/api/site/{site}/trafficroutes` (policy-based routing paradigm)
    - Missing: Traditional metric field
    - Phase 2 implementation

### Web/Elasticsearch Reader (1)

58. **Document**
    - doc_id, source_url, source_type, content_hash, ingested_at, extraction_state

---

## Temporal Tracking (ALL Entities)

Every node and relationship MUST include:

```python
# Node properties
created_at: datetime          # When we created this node
updated_at: datetime          # When we last modified this node
source_timestamp: datetime    # When the source content was created (if available)
extraction_tier: str          # "A", "B", or "C"
extraction_method: str        # "regex", "spacy_ner", "qwen3_llm", "github_api", etc.
confidence: float             # 0.0-1.0 (1.0 for Tier A, variable for B/C)
extractor_version: str        # Version of extractor that created this

# Relationship properties
created_at: datetime
source_timestamp: datetime
source: str                   # Ingestion job ID or reader type
confidence: float
```

---

## Relationship Schemas (Pydantic)

### Base Relationship

```python
class BaseRelationship(BaseModel):
    created_at: datetime
    source_timestamp: Optional[datetime] = None
    source: str  # job_id or reader type
    confidence: float = 1.0
    extractor_version: str
```

### Specific Relationships

**MENTIONS** (Document → Entity):
```python
class MentionsRelationship(BaseRelationship):
    span: str  # Text snippet
    section: str  # Document section
    chunk_id: UUID
```

**WORKS_AT** (Person → Organization):
```python
class WorksAtRelationship(BaseRelationship):
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
```

**ROUTES_TO** (Proxy → Service via ProxyRoute):
```python
class RoutesToRelationship(BaseRelationship):
    host: str  # server_name
    path: str  # location path
    tls: bool
    auth_enabled: bool
```

**DEPENDS_ON** (ComposeService → ComposeService):
```python
class DependsOnRelationship(BaseRelationship):
    condition: str  # service_started, service_healthy
```

**SENT** (Person → Email):
```python
class SentRelationship(BaseRelationship):
    sent_at: datetime
```

**CONTRIBUTES_TO** (Person → Repository):
```python
class ContributesToRelationship(BaseRelationship):
    commit_count: int
    first_commit_at: datetime
    last_commit_at: datetime
```

---

## Relationship Direction Conventions

Establish conventions but support bidirectional queries:

- `(:Person)-[:WORKS_AT]->(:Organization)` - Subject to object
- `(:Document)-[:MENTIONS]->(:Entity)` - Source to target
- `(:File)-[:BELONGS_TO]->(:Space)` - Child to parent (future)
- `(:Person)-[:CREATED]->(:File)` - Creator to creation
- `(:Repository)-[:DEPENDS_ON]->(:Package)` - Dependent to dependency
- `(:ComposeService)-[:DEPENDS_ON]->(:ComposeService)` - Requires to required
- `(:Email)-[:IN_THREAD]->(:Thread)` - Member to container
- `(:ProxyRoute)-[:ROUTES_TO]->(:ComposeService)` - Router to backend

---

## Research Requirements

### Unifi API Capabilities (✅ RESEARCH COMPLETE)

**Research Summary:**
All 5 rule types are extractable from Unifi Controller API with varying levels of support:

**Phase 1 - Full Support (3 types):**
1. ✅ **Port Forwarding Rules**: `/api/s/{site}/rest/portforward`
   - All required fields available (proto, src, dst_port, fwd, fwd_port)
   - Works across all controller versions

2. ✅ **Firewall Rules**: `/v2/api/site/{site}/firewall-policies`
   - Zone-based addressing with full support
   - Requires UniFi Network Application 7.0+
   - Alternative legacy endpoint: `/api/s/{site}/rest/firewallrule` (limited)

3. ✅ **TrafficRule (QoS/Traffic Shaping)**: `/v2/api/site/{site}/trafficrules`
   - Bandwidth limiting (download_kbps, upload_kbps)
   - IP/domain/application targeting
   - Schedule-based rules
   - Requires UniFi Network Application 7.0+

**Phase 2 - Partial Support (2 types):**
4. ⚠️ **TrafficRoute (Static Routes)**: `/v2/api/site/{site}/trafficroutes`
   - Available via traffic routes with `next_hop` field
   - Uses policy-based routing paradigm (not traditional static routes)
   - Missing: Traditional metric field for route priority
   - Workaround: Extract routes with IP matching + next_hop

5. ⚠️ **NATRule**: DNAT only via port forwarding
   - DNAT: Available through `/api/s/{site}/rest/portforward`
   - SNAT/Masquerade: Not exposed via API (UI only)
   - Workaround: Extract DNAT rules as subset of port forwarding

**API Version Requirements:**
- Legacy API (`/api/s/{site}/rest/*`): UniFi Controller 5.x-6.x
- Modern v2 API (`/v2/api/site/{site}/*`): UniFi Network Application 7.0+ (recommended)
- Note: Legacy `/rest/routing` endpoint unreliable (HTTP 500 errors in v7.1.66)

---

## Extraction Details by Reader

### Docker Compose (Tier A - Deterministic)

**Extraction targets**:
- Parse YAML with PyYAML
- Create ComposeFile root entity
- Extract all services, networks, volumes
- Create separate entities for:
  - Each environment variable (queryable: "Find all services using SECRET_KEY")
  - Each port binding (queryable: "Find all services exposing port 8080")
  - Each dependency (queryable: "Find all services depending on postgres")
  - Each healthcheck (queryable: "Find all unhealthy services")
  - Each build context (queryable: "Find all services built from Dockerfile")
  - Each device mapping (queryable: "Find all services with GPU access")

### SWAG (Tier A - Deterministic)

**Extraction targets**:
- Parse nginx config with regex
- Create SwagConfigFile root entity
- Extract nginx variables:
  ```nginx
  set $upstream_app 100.74.16.82;
  set $upstream_port 3005;
  set $upstream_proto http;
  ```
- Extract `server_name` from server blocks
- Extract all `location` blocks with:
  - Path pattern
  - `proxy_pass` URL
  - Auth check: `include /config/nginx/authelia-location.conf` present?
- Extract headers as separate entities:
  - `add_header X-Custom-Header "value"`
  - `proxy_set_header Host $host`
- Create separate entities for queryability:
  - "Find all routes with auth enabled"
  - "Find all routes setting X-Frame-Options header"
  - "Find all backends on port 3000"

### GitHub (Tier A - Deterministic)

**Extraction targets**:
- Use GitHub REST API (not just file content)
- Map User → Person, Org → Organization
- Create Release entity (distinct from Tags)
- Handle file types:
  - Documentation (README.md, docs/*) → Documentation entity
  - Config files (docker-compose.yml) → Pass to respective reader
  - Binary assets → BinaryAsset entity (reference only)
  - Code files → Store metadata only (AST extraction is Phase 2)

### Gmail (Tier A + Tier B)

**Extraction targets**:
- Tier A: Email headers, metadata, attachments (Gmail API)
- Tier B: Body analysis with spaCy (extract Person/Organization mentions)
- Map contacts → Person entities
- Thread conversations with REPLY_TO relationships

### Tailscale (Tier A - Deterministic)

**Extraction targets**:
- API: `/api/v2/tailnet/{tailnet}/devices`
- Extract all fields: OS, IPv4/IPv6, hostname, endpoints, key expiry, exit node, subnet routes, SSH, DNS
- Create TailscaleACL entities from ACL endpoint (if available)

### Unifi (Tier A - Deterministic)

**Extraction targets**:
- Devices: MAC, IP, name, firmware, link speed, connection type, uptime
- Clients: MAC, IP, hostname, network, wired/wireless, uptime
- Networks: VLAN, subnet, gateway, DNS, WiFi name
- Sites: WAN IP, gateway, DNS

**Phase 1 - Network Rules (Full Support)**:
- **Port Forwarding**: `/api/s/{site}/rest/portforward`
  - Extract: proto, src, dst_port, fwd (internal IP), fwd_port, pfwd_interface
- **Firewall Policies**: `/v2/api/site/{site}/firewall-policies`
  - Extract: action, protocol, source_zone, dest_zone, index (priority), logging
  - Zone mappings via `/v2/api/site/{site}/firewall-zones`
- **Traffic Rules (QoS)**: `/v2/api/site/{site}/trafficrules`
  - Extract: bandwidth limits (download_kbps, upload_kbps), IP/domain targets, schedule

**Phase 2 - Advanced Rules (Partial Support)**:
- **Traffic Routes (Static Routes)**: `/v2/api/site/{site}/trafficroutes`
  - Extract: next_hop (gateway), IP/domain matching, network_id
  - Note: Uses policy-based routing, missing traditional metric field
- **NAT Rules**: DNAT only via port forwarding (SNAT not available)

### Reddit (Tier A - Deterministic)

**Extraction targets**:
- Reddit API via PRAW
- Subreddit metadata
- Posts with full metadata (score, comments, timestamps)
- Comment threads with parent-child relationships

### YouTube (Tier A + Optional Tier C)

**Extraction targets**:
- Tier A: Video metadata via YouTube Data API
- Tier A: Transcript text via YouTube Transcript API
- Optional Tier C: Semantic analysis of transcript content

### Web/Elasticsearch (Tier A for ES, Tier A/B/C for Web)

**Extraction targets**:
- ES: Deterministic field extraction from JSON documents
- Web: Firecrawl + Normalizer + Chunker → downstream extraction

---

## File Deletion Plan

### Schemas to Delete

```
packages/schemas/models/__init__.py
  - Delete: Service (lines 312-324)
  - Delete: Host (lines 326-336)
  - Delete: IP (lines 338-348)
  - Delete: Proxy (lines 351-360) [will recreate with new properties]
  - Delete: Endpoint (lines 362-372)
  - Keep: Doc (lines 108-120) [rename to Document]
```

### Writers to Delete

```
packages/graph/writers/
  - Keep: swag_writer.py (update for new entities)
  - Delete: batched.py (unused legacy)
  - Keep: __init__.py (update exports)
```

### Tests to Delete

**Complete Deletion (4 files, ~723 lines):**

```
tests/packages/schemas/
  - test_graph_nodes.py (343 lines) - Tests old Service, Host, IP, Proxy, Endpoint entities
  - test_extraction_job.py (281 lines) - Tests 3-tier extraction system (being removed)
  - test_extraction_window.py (196 lines) - Tests 3-tier extraction system (being removed)

tests/packages/graph/
  - test_writers.py (63 lines) - Tests legacy BatchedGraphWriter

tests/integration/
  - test_ingest_creates_document_records.py (40 lines) - Uses old Document extraction_state model
```

**Major Rewrites (6 files, ~4,049 lines):**

```
tests/packages/ingest/readers/ (ALL 10 reader tests - ~2,327 lines)
  - test_web_reader.py (299 lines)
  - test_docker_compose.py (327 lines)
  - test_github.py (69 lines)
  - test_reddit.py (74 lines)
  - test_youtube.py (68 lines)
  - test_gmail.py (60 lines)
  - test_elasticsearch.py (58 lines)
  - test_unifi.py (616 lines)
  - test_swag.py (358 lines)
  - test_tailscale.py (397 lines)

tests/integration/
  - test_init_e2e.py (295 lines) - Rewrite constraint validation for 63 new constraints
  - test_ingest_structured_e2e.py (580 lines) - Complete rewrite for new entity model
  - test_extract_e2e.py (658 lines) - Rewrite for Entity/Claim model

tests/packages/core/use_cases/
  - test_extract_pending.py (355 lines) - Update entity type assertions
```

**Minor Updates (6 files, ~634 lines):**

```
tests/packages/graph/
  - test_constraints.py (45 lines) - Update constraint count to 63, spot-check validations

tests/integration/
  - test_query_e2e.py (159 lines) - Update test queries for new entity model

tests/packages/core/use_cases/
  - test_ingest_web.py (428 lines) - Minor metadata updates for new Document schema

tests/apps/cli/
  - test_cli_ingest_docker_compose.py (5 references to BatchedGraphWriter)

tests/integration/
  - test_extract_e2e.py (1 reference to BatchedGraphWriter)
  - test_ingest_structured_e2e.py (1 reference to BatchedGraphWriter)
```

**Keep As-Is (7 files, ~2,172 lines):**

```
tests/packages/schemas/
  - test_models.py (363 lines) - Document, Chunk, IngestionJob models
  - test_api_key.py (42 lines) - ApiKey authentication model

tests/packages/graph/
  - test_cypher_builders.py (63 lines)
  - test_neo4j_client.py
  - test_traversal.py

tests/packages/core/use_cases/
  - test_get_status.py (267 lines)
  - test_reprocess.py (111 lines)
  - test_query.py (62 lines)
  - test_list_documents_use_case.py (205 lines)

tests/integration/
  - test_metrics_e2e.py (617 lines)
  - test_ingest_web_e2e.py (380 lines)
  - test_ingest_apis_e2e.py (229 lines)
```

**Missing Tests (Need Creation - 3 files, ~750 lines):**

```
tests/packages/core/use_cases/
  - test_ingest_swag.py (~200 lines) - Test SwagReader → GraphWriter pipeline
  - test_ingest_elasticsearch.py (~300 lines) - Test ElasticsearchReader pipeline
  - test_ingest_youtube.py (~250 lines) - Test YoutubeReader pipeline
```

**Total Test Effort:**
- **Delete**: 4 files (~723 lines)
- **Major Rewrite**: 16 files (~4,049 lines)
- **Minor Update**: 6 files (~634 lines)
- **Keep As-Is**: 10 files (~2,172 lines)
- **Create New**: 3 files (~750 lines)

### Constraints to Replace

```
specs/001-taboot-rag-platform/contracts/
  - Replace: neo4j-constraints.cypher (complete rewrite)
```

---

## File Creation Plan

### Schemas to Create (63 files)

```
packages/schemas/core/
  - person.py
  - organization.py
  - place.py
  - event.py
  - file.py

packages/schemas/docker_compose/
  - compose_file.py
  - compose_project.py
  - compose_service.py
  - compose_network.py
  - compose_volume.py
  - port_binding.py
  - environment_variable.py
  - service_dependency.py
  - image_details.py
  - health_check.py
  - build_context.py
  - device_mapping.py

packages/schemas/swag/
  - swag_config_file.py
  - proxy.py
  - proxy_route.py
  - location_block.py
  - upstream_config.py
  - proxy_header.py

packages/schemas/github/
  - repository.py
  - issue.py
  - pull_request.py
  - commit.py
  - branch.py
  - tag.py
  - github_label.py
  - milestone.py
  - comment.py
  - release.py
  - documentation.py
  - binary_asset.py

packages/schemas/gmail/
  - email.py
  - thread.py
  - gmail_label.py
  - attachment.py

packages/schemas/reddit/
  - subreddit.py
  - reddit_post.py
  - reddit_comment.py

packages/schemas/youtube/
  - video.py
  - channel.py
  - transcript.py

packages/schemas/tailscale/
  - tailscale_device.py
  - tailscale_network.py
  - tailscale_acl.py

packages/schemas/unifi/
  - unifi_device.py
  - unifi_client.py
  - unifi_network.py
  - unifi_site.py
  - port_forwarding_rule.py (if API supports)
  - firewall_rule.py (if API supports)
  - nat_rule.py (if API supports)
  - qos_rule.py (if API supports)
  - static_route.py (if API supports)

packages/schemas/relationships/
  - base.py (BaseRelationship)
  - mentions.py
  - works_at.py
  - routes_to.py
  - depends_on.py
  - sent.py
  - contributes_to.py
  - (20+ relationship schemas)
```

### Writers to Create (15 files)

```
packages/graph/writers/
  - person_writer.py
  - organization_writer.py
  - place_writer.py
  - event_writer.py
  - file_writer.py
  - docker_compose_writer.py
  - swag_writer.py (update existing)
  - github_writer.py
  - gmail_writer.py
  - reddit_writer.py
  - youtube_writer.py
  - tailscale_writer.py
  - unifi_writer.py
  - document_writer.py
  - relationship_writer.py
```

### Tests to Delete (5 files)

```
tests/packages/schemas/
  - test_graph_nodes.py (343 lines) - OLD: Service, Host, IP, Proxy, Endpoint entities
  - test_extraction_job.py (281 lines) - OLD: 3-tier extraction system
  - test_extraction_window.py (196 lines) - OLD: 3-tier extraction system

tests/packages/graph/
  - test_writers.py (63 lines) - OLD: Legacy BatchedGraphWriter

tests/integration/
  - test_ingest_creates_document_records.py (40 lines) - OLD: Document extraction_state model
```

**Total: 5 files, ~923 lines to delete**

### Tests to Create (37 files)

```
tests/packages/schemas/ (10 files)
  - test_core_entities.py
  - test_docker_compose_entities.py
  - test_swag_entities.py
  - test_github_entities.py
  - test_gmail_entities.py
  - test_reddit_entities.py
  - test_youtube_entities.py
  - test_tailscale_entities.py
  - test_unifi_entities.py
  - test_relationships.py

tests/packages/graph/writers/ (15 files)
  - test_person_writer.py
  - test_organization_writer.py
  - test_place_writer.py
  - test_event_writer.py
  - test_file_writer.py
  - test_docker_compose_writer.py
  - test_swag_writer.py
  - test_github_writer.py
  - test_gmail_writer.py
  - test_reddit_writer.py
  - test_youtube_writer.py
  - test_tailscale_writer.py
  - test_unifi_writer.py
  - test_document_writer.py
  - test_relationship_writer.py

tests/integration/ (9 files)
  - test_docker_compose_e2e.py
  - test_swag_e2e.py
  - test_github_e2e.py
  - test_gmail_e2e.py
  - test_reddit_e2e.py
  - test_youtube_e2e.py
  - test_tailscale_e2e.py
  - test_unifi_e2e.py
  - test_infrastructure_correlation_e2e.py

tests/packages/core/use_cases/ (3 files)
  - test_ingest_swag.py (~200 lines) - MISSING: SwagReader → GraphWriter pipeline
  - test_ingest_elasticsearch.py (~300 lines) - MISSING: ElasticsearchReader pipeline
  - test_ingest_youtube.py (~250 lines) - MISSING: YoutubeReader pipeline
```

**Total: 37 new test files**

---

## Implementation Phases

### Phase 0: Research & Preparation (2-4h)

**Tasks:**
1. ✅ Dispatch Unifi API research agent
2. ✅ Wait for research completion
3. ✅ Finalize entity list based on API capabilities
4. ✅ Create complete file manifest (delete/update/create)
5. ✅ Set up TDD framework and test templates

**Gate**: All research complete, file manifest approved

### Phase 1: Core Schemas (TDD, Sequential, 12-14h)

**Agent**: 1 programmer

**Tasks** (RED-GREEN-REFACTOR for each):
1. ✅ Write failing test for Person entity
2. ✅ Implement Person entity (pass test)
3. ✅ Refactor Person entity
4. Repeat for: Organization, Place, Event, File
5. ✅ Write failing test for BaseRelationship
6. ✅ Implement BaseRelationship (pass test)
7. ✅ Refactor BaseRelationship
8. Repeat for: 10 core relationship types
9. ✅ Update Neo4j constraints file with core entities
10. ✅ Verify constraints apply: `SHOW CONSTRAINTS`

**Checkpoints**:
- [ ] All core entity tests pass
- [ ] All relationship schema tests pass
- [ ] Neo4j constraints applied successfully

**Gate**: Core schemas complete, all tests green, constraints verified

### Phase 2: Reader-Specific Schemas (TDD, Parallel, 8-10h wall-clock)

**Agents**: 8 programmers (max 10 constraint, reserve 2 for monitoring)

**Agent 1**: Docker Compose entities (12 models)
**Agent 2**: SWAG entities (6 models)
**Agent 3**: GitHub entities (12 models)
**Agent 4**: Gmail entities (4 models)
**Agent 5**: Reddit entities (3 models)
**Agent 6**: YouTube entities (3 models)
**Agent 7**: Tailscale entities (3 models)
**Agent 8**: Unifi entities (4-9 models depending on API research)

**TDD Pattern for Each Agent**:
```
For each entity type:
1. Write failing test
2. Implement entity (pass test)
3. Refactor
4. Mark checkbox in plan
5. Update Neo4j constraints file
```

**Checkpoints** (per agent):
- [ ] All entity tests pass
- [ ] Constraints added to neo4j-constraints.cypher
- [ ] Progress checkboxes marked

**Gate**: All 58 reader-specific entities complete, all tests green

### Phase 3: Graph Writers (TDD, Parallel, 6-8h wall-clock)

**Agents**: 10 programmers (2 handle multiple writers)

**Agent 1**: PersonWriter + OrganizationWriter
**Agent 2**: PlaceWriter + EventWriter + FileWriter
**Agent 3**: DockerComposeWriter
**Agent 4**: SwagWriter (update existing)
**Agent 5**: GitHubWriter
**Agent 6**: GmailWriter
**Agent 7**: RedditWriter + YouTubeWriter
**Agent 8**: TailscaleWriter
**Agent 9**: UnifiWriter
**Agent 10**: DocumentWriter + RelationshipWriter

**TDD Pattern**:
```
For each writer:
1. Write failing test (empty list, single entity, batch 2000, idempotent, constraint violations)
2. Implement writer following SwagGraphWriter pattern (2000-row UNWIND batches)
3. Refactor
4. Mark checkbox
5. Verify ≥95% coverage
```

**Checkpoints** (per agent):
- [ ] All writer tests pass
- [ ] Coverage ≥95%
- [ ] Performance: ≥20k edges/min
- [ ] Progress checkboxes marked

**Gate**: All 15 writers complete, all tests green, coverage ≥95%

### Phase 4: Reader Updates (TDD, Parallel, 4-6h wall-clock)

**Agents**: 8 programmers

**Agent 1**: Update docker_compose reader
**Agent 2**: Update swag reader
**Agent 3**: Update github reader
**Agent 4**: Update gmail reader
**Agent 5**: Update reddit reader
**Agent 6**: Update youtube reader
**Agent 7**: Update tailscale reader
**Agent 8**: Update unifi reader

**TDD Pattern**:
```
For each reader:
1. Write failing integration test (read source → extract entities)
2. Update reader to output new entity types
3. Refactor
4. Mark checkbox
```

**Checkpoints** (per agent):
- [ ] Reader outputs new entity types
- [ ] Integration test passes
- [ ] Progress checkboxes marked

**Gate**: All readers updated, all integration tests green

### Phase 5: Use-Case Updates (TDD, Parallel, 4-6h wall-clock)

**Agents**: 8 programmers

**Agent 1**: Update ingest_docker_compose use-case
**Agent 2**: Update ingest_swag use-case
**Agent 3**: Update ingest_github use-case
**Agent 4**: Update ingest_gmail use-case
**Agent 5**: Update ingest_reddit use-case
**Agent 6**: Update ingest_youtube use-case
**Agent 7**: Update ingest_tailscale use-case
**Agent 8**: Update ingest_unifi use-case

**Tasks**:
```
For each use-case:
1. Update to call new writers
2. Update to use new entity types
3. Add temporal tracking
4. Verify e2e flow
```

**Checkpoints** (per agent):
- [ ] Use-case updated
- [ ] E2E test passes
- [ ] Progress checkboxes marked

**Gate**: All use-cases updated, all e2e tests green

### Phase 6: Verification (Parallel, 2-3h wall-clock)

**Agents**: 10 verification agents

**Agent 1**: Verify all deleted files removed
**Agent 2**: Verify all updated files modified correctly
**Agent 3**: Verify all created files exist
**Agent 4**: Run full test suite (unit tests)
**Agent 5**: Run integration tests
**Agent 6**: Verify Neo4j constraints (SHOW CONSTRAINTS = 63 constraints)
**Agent 7**: Performance benchmarks (≥20k edges/min)
**Agent 8**: Coverage report (≥95% for writers)
**Agent 9**: End-to-end smoke tests (ingest → extract → query)
**Agent 10**: Documentation validation

**Checklist**:
- [ ] All deleted files removed
- [ ] All updated files modified
- [ ] All created files exist
- [ ] Unit tests: 100% pass
- [ ] Integration tests: 100% pass
- [ ] Neo4j constraints: 63 total
- [ ] Performance: ≥20k edges/min
- [ ] Coverage: ≥95% writers
- [ ] E2E smoke tests pass
- [ ] Docs updated

**Gate**: All verification checks pass

---

## Success Metrics

### Functional Completeness
- ✅ 5 core + 58 reader-specific entities = 63 total
- ✅ All entities have temporal tracking
- ✅ All relationships have Pydantic schemas
- ✅ All 15 writers implement write_* methods
- ✅ All 10 readers output new entity types
- ✅ Neo4j constraints: 63 total

### Test Coverage
- ✅ Unit tests: <10s total
- ✅ Integration tests: <2min total
- ✅ Coverage: ≥95% for packages/graph/writers/
- ✅ All TDD cycles complete (red → green → refactor)

### Performance
- ✅ Writer throughput: ≥20k edges/min (333 edges/sec)
- ✅ Neo4j UNWIND batches: 2000 rows
- ✅ Extraction: ≥50 pages/sec (Tier A)

---

## Out of Scope (Phase 2)

**NOT included in this refactor:**
- ❌ Code AST extraction with treesitter
- ❌ Cross-source enrichment/correlation
- ❌ Infrastructure topology correlation
- ❌ Spaces implementation (node or property-based)
- ❌ GitHub + Firecrawl correlation
- ❌ Gmail + Calendar + Contacts enrichment
- ❌ YouTube + Reddit correlation

These features will be implemented after core refactor is complete and stable.

---

## Risk Mitigation

### High Severity
1. **Constraint violations on existing data**
   - Mitigation: Wipe Neo4j volume before applying new constraints
   - Command: `docker volume rm taboot_neo4j_data`

2. **Unifi API capabilities unknown**
   - Mitigation: Research agent validates API before implementation
   - Fallback: Mark as Phase 2 if API doesn't support

### Medium Severity
3. **Parallel agent coordination**
   - Mitigation: Phase gates enforce completion before proceeding
   - Mitigation: Progress checkboxes tracked by each agent

4. **Test data cleanup**
   - Mitigation: Pytest fixtures with teardown
   - Mitigation: `MATCH (n) DETACH DELETE n` after each test

### Low Severity
5. **Performance degradation**
   - Mitigation: Benchmark before/after, <20% overhead acceptable
   - Mitigation: Each constraint adds ~10-15% write overhead

---

## Next Steps

1. ✅ Review this document
2. ✅ Dispatch Unifi API research agent (1-2h)
3. ✅ Wait for research completion
4. ✅ Finalize entity list based on API findings (63 total: 5 core + 58 reader-specific)
5. ⏳ Create detailed implementation plan with task breakdown
6. ⏳ Execute Phase 0 (preparation)
7. ⏳ Execute Phase 1 (core schemas)
8. ⏳ Execute Phase 2-6 (parallel implementation)
9. ⏳ Verification and sign-off

**Estimated Total Time**: 50-60 hours wall-clock with aggressive parallelization

---

## Questions for User

1. ✅ Separate entities vs properties for Docker env vars, SWAG headers, etc? → **ANSWERED: Separate entities**
2. ✅ Unifi API capabilities for port forwarding/firewall/NAT/QoS/routes? → **ANSWERED: 3 full support, 2 partial support**
3. ✅ Code AST extraction in scope? → **ANSWERED: Phase 2**
4. ✅ Enrichment/correlation in scope? → **ANSWERED: Phase 2**
5. ✅ Spaces implementation in scope? → **ANSWERED: Phase 2**

---

**Document Status**: Ready for implementation planning
**Last Updated**: 2025-10-28
**Next Action**: Create detailed implementation plan with task breakdown and checkboxes
