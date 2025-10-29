# Implementation Tasks: Neo4j Graph Architecture Refactor

**Project**: Neo4j Graph Architecture Refactor
**Created**: 2025-10-28
**Status**: Planning Phase → Implementation Ready
**Total Tasks**: 157
**Development Method**: TDD (Red-Green-Refactor)
**Max Parallel Agents**: 10

## Summary

This task list implements the complete refactor from domain-specific entities (Service, Host, IP) to a flexible core + reader-specific model (5 core + 53 reader-specific entities = 58 total). The refactor enables multi-source RAG with temporal tracking, relationship validation, and infrastructure correlation.

**Key Points**:
- **NO backwards compatibility** - Full rewrite, database wipe required
- **TDD mandatory**: Write failing test (RED) → Min code to pass (GREEN) → Refactor
- **Parallel execution**: Max 10 agents simultaneously (reserve 2 for monitoring)
- **Use `[P]` marker** for parallelizable tasks (different files, no dependencies)
- **Each phase** is independently testable with clear completion gates
- **Temporal tracking** on ALL nodes and relationships (created_at, updated_at, source_timestamp, etc.)

**Architecture Changes**:
- **5 core entities**: Person, Organization, Place, Event, File
- **53 reader-specific entities**: Docker Compose (12), SWAG (6), GitHub (12), Gmail (4), Reddit (3), YouTube (3), Tailscale (3), Unifi (9), Web/ES (1)
- **Pydantic schemas** for ALL relationships
- **Separate entities** for properties (env vars, headers, rules) for maximum queryability
- **Neo4j constraints**: 58 total (up from 5)

**Estimated Timeline**: 50-60 hours wall-clock with aggressive parallelization

---

## Phase 0: Research & Preparation (COMPLETED ✅)

**Goal**: Validate all research complete, finalize entity list, set up TDD framework.

**Status**: ✅ Research complete (Unifi API research complete, entity list finalized)

### Tasks

- [X] R001 ✅ Dispatch Unifi API research agent
- [X] R002 ✅ Wait for research completion
- [X] R003 ✅ Finalize entity list based on API capabilities (58 total: 5 core + 53 reader-specific)
- [X] R004 ✅ Create complete file manifest (delete/update/create)
- [X] R005 ✅ Set up TDD framework and test templates

**Gate**: ✅ ALL RESEARCH COMPLETE - Entity list approved, file manifest ready

---

## Phase 1: Core Schemas (TDD, Sequential, 12-14h)

**Goal**: Implement 5 core entities + base relationship schema + 10 core relationship types.

**Agent**: 1 programmer (sequential TDD for foundational types)

**Completion Criteria**:
- [X] All core entity tests pass
- [X] All relationship schema tests pass
- [X] Neo4j constraints applied successfully
- [X] Coverage ≥95% (verified via `uv run pytest --cov=packages/schemas/core tests/packages/schemas/core`)

### Core Entity Implementation (RED-GREEN-REFACTOR)

- [X] T001 [P1] Write failing test for Person entity in tests/packages/schemas/core/test_person.py
- [X] T002 [P1] Implement Person entity in packages/schemas/core/person.py (name, email, role, bio, github_username, reddit_username, youtube_channel + temporal fields)
- [X] T003 [P1] Refactor Person entity (validate constraints, optimize field types)

- [X] T004 [P1] Write failing test for Organization entity in tests/packages/schemas/core/test_organization.py
- [X] T005 [P1] Implement Organization entity in packages/schemas/core/organization.py (name, industry, size, website, description + temporal fields)
- [X] T006 [P1] Refactor Organization entity

- [X] T007 [P1] Write failing test for Place entity in tests/packages/schemas/core/test_place.py
- [X] T008 [P1] Implement Place entity in packages/schemas/core/place.py (name, address, coordinates, place_type + temporal fields)
- [X] T009 [P1] Refactor Place entity

- [X] T010 [P1] Write failing test for Event entity in tests/packages/schemas/core/test_event.py
- [X] T011 [P1] Implement Event entity in packages/schemas/core/event.py (name, start_time, end_time, location, event_type + temporal fields)
- [X] T012 [P1] Refactor Event entity

- [X] T013 [P1] Write failing test for File entity in tests/packages/schemas/core/test_file.py
- [X] T014 [P1] Implement File entity in packages/schemas/core/file.py (name, file_id, source, mime_type, size_bytes, url + temporal fields)
- [X] T015 [P1] Refactor File entity

### Base Relationship Schema (RED-GREEN-REFACTOR)

- [X] T016 [P1] Write failing test for BaseRelationship in tests/packages/schemas/relationships/test_base.py
- [X] T017 [P1] Implement BaseRelationship in packages/schemas/relationships/base.py (created_at, source_timestamp, source, confidence, extractor_version)
- [X] T018 [P1] Refactor BaseRelationship

### Core Relationship Types (RED-GREEN-REFACTOR for each)

- [X] T019 [P] [P1] Write failing test for MentionsRelationship in tests/packages/schemas/relationships/test_mentions.py
- [X] T020 [P] [P1] Implement MentionsRelationship in packages/schemas/relationships/mentions.py (span, section, chunk_id + base fields)

- [X] T021 [P] [P1] Write failing test for WorksAtRelationship in tests/packages/schemas/relationships/test_works_at.py
- [X] T022 [P] [P1] Implement WorksAtRelationship in packages/schemas/relationships/works_at.py (role, start_date, end_date + base fields)

- [X] T023 [P] [P1] Write failing test for RoutesToRelationship in tests/packages/schemas/relationships/test_routes_to.py
- [X] T024 [P] [P1] Implement RoutesToRelationship in packages/schemas/relationships/routes_to.py (host, path, tls, auth_enabled + base fields)

- [X] T025 [P] [P1] Write failing test for DependsOnRelationship in tests/packages/schemas/relationships/test_depends_on.py
- [X] T026 [P] [P1] Implement DependsOnRelationship in packages/schemas/relationships/depends_on.py (condition + base fields)

- [X] T027 [P] [P1] Write failing test for SentRelationship in tests/packages/schemas/relationships/test_sent.py
- [X] T028 [P] [P1] Implement SentRelationship in packages/schemas/relationships/sent.py (sent_at + base fields)

- [X] T029 [P] [P1] Write failing test for ContributesToRelationship in tests/packages/schemas/relationships/test_contributes_to.py
- [X] T030 [P] [P1] Implement ContributesToRelationship in packages/schemas/relationships/contributes_to.py (commit_count, first_commit_at, last_commit_at + base fields)

- [X] T031 [P] [P1] Write failing test for CreatedRelationship in tests/packages/schemas/relationships/test_created.py
- [X] T032 [P] [P1] Implement CreatedRelationship in packages/schemas/relationships/created.py (base fields only)

- [X] T033 [P] [P1] Write failing test for BelongsToRelationship in tests/packages/schemas/relationships/test_belongs_to.py
- [X] T034 [P] [P1] Implement BelongsToRelationship in packages/schemas/relationships/belongs_to.py (base fields only)

- [X] T035 [P] [P1] Write failing test for InThreadRelationship in tests/packages/schemas/relationships/test_in_thread.py
- [X] T036 [P] [P1] Implement InThreadRelationship in packages/schemas/relationships/in_thread.py (base fields only)

- [X] T037 [P] [P1] Write failing test for LocatedInRelationship in tests/packages/schemas/relationships/test_located_in.py
- [X] T038 [P] [P1] Implement LocatedInRelationship in packages/schemas/relationships/located_in.py (base fields only)

### Neo4j Constraints for Core Entities

- [X] T039 [P1] Update specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher with core entity constraints (Person, Organization, Place, Event, File)
- [X] T040 [P1] Verify core constraints apply: Run `SHOW CONSTRAINTS` in Neo4j and validate 5 core constraints exist

**Checkpoint**: Core schemas complete, all tests green, constraints verified

---

## Phase 2: Reader-Specific Schemas (TDD, Parallel, 8-10h wall-clock)

**Goal**: Implement 53 reader-specific entities across 8 parallel agents.

**Agents**: 8 programmers (max 10 constraint, reserve 2 for monitoring)

**Agent Assignment**:
- **Agent 1**: Docker Compose entities (12 models) - T041-T064
- **Agent 2**: SWAG entities (6 models) - T065-T076
- **Agent 3**: GitHub entities (12 models) - T077-T100
- **Agent 4**: Gmail entities (4 models) - T101-T108
- **Agent 5**: Reddit entities (3 models) - T109-T114
- **Agent 6**: YouTube entities (3 models) - T115-T120
- **Agent 7**: Tailscale entities (3 models) - T121-T126
- **Agent 8**: Unifi entities (9 models) - T127-T144

**TDD Pattern for Each Agent**:
```
For each entity type:
1. Write failing test
2. Implement entity (pass test)
3. Refactor
4. Update Neo4j constraints file
```

**Completion Criteria (per agent)**:
- [X] All entity tests pass (see `uv run pytest --cov=...` runs for docker_compose, swag, github, gmail, reddit, youtube, tailscale, unifi, web)
- [X] Constraints added to neo4j-constraints.cypher
- [X] Coverage ≥95% (all schema suites at ≥96% after direct validator tests)
- [X] Progress checkboxes marked

### Agent 1: Docker Compose Entities (12 models)

- [X] T041 [P] [P2-DC] Write test for ComposeFile in tests/packages/schemas/docker_compose/test_compose_file.py
- [X] T042 [P] [P2-DC] Implement ComposeFile in packages/schemas/docker_compose/compose_file.py (file_path, version, project_name + temporal)

- [X] T043 [P] [P2-DC] Write test for ComposeProject in tests/packages/schemas/docker_compose/test_compose_project.py
- [X] T044 [P] [P2-DC] Implement ComposeProject in packages/schemas/docker_compose/compose_project.py (name, version, file_path + temporal)

- [X] T045 [P] [P2-DC] Write test for ComposeService in tests/packages/schemas/docker_compose/test_compose_service.py
- [X] T046 [P] [P2-DC] Implement ComposeService in packages/schemas/docker_compose/compose_service.py (name, image, command, entrypoint, restart, cpus, memory, user, working_dir, hostname + temporal)

- [X] T047 [P] [P2-DC] Write test for ComposeNetwork in tests/packages/schemas/docker_compose/test_compose_network.py
- [X] T048 [P] [P2-DC] Implement ComposeNetwork in packages/schemas/docker_compose/compose_network.py (name, driver, external, enable_ipv6, ipam_driver, ipam_config + temporal)

- [X] T049 [P] [P2-DC] Write test for ComposeVolume in tests/packages/schemas/docker_compose/test_compose_volume.py
- [X] T050 [P] [P2-DC] Implement ComposeVolume in packages/schemas/docker_compose/compose_volume.py (name, driver, external, driver_opts + temporal)

- [X] T051 [P] [P2-DC] Write test for PortBinding in tests/packages/schemas/docker_compose/test_port_binding.py
- [X] T052 [P] [P2-DC] Implement PortBinding in packages/schemas/docker_compose/port_binding.py (host_ip, host_port, container_port, protocol + temporal)

- [X] T053 [P] [P2-DC] Write test for EnvironmentVariable in tests/packages/schemas/docker_compose/test_environment_variable.py
- [X] T054 [P] [P2-DC] Implement EnvironmentVariable in packages/schemas/docker_compose/environment_variable.py (key, value, service_name + temporal)

- [X] T055 [P] [P2-DC] Write test for ServiceDependency in tests/packages/schemas/docker_compose/test_service_dependency.py
- [X] T056 [P] [P2-DC] Implement ServiceDependency in packages/schemas/docker_compose/service_dependency.py (source_service, target_service, condition + temporal)

- [X] T057 [P] [P2-DC] Write test for ImageDetails in tests/packages/schemas/docker_compose/test_image_details.py
- [X] T058 [P] [P2-DC] Implement ImageDetails in packages/schemas/docker_compose/image_details.py (image_name, tag, registry, digest + temporal)

- [X] T059 [P] [P2-DC] Write test for HealthCheck in tests/packages/schemas/docker_compose/test_health_check.py
- [X] T060 [P] [P2-DC] Implement HealthCheck in packages/schemas/docker_compose/health_check.py (test, interval, timeout, retries, start_period + temporal)

- [X] T061 [P] [P2-DC] Write test for BuildContext in tests/packages/schemas/docker_compose/test_build_context.py
- [X] T062 [P] [P2-DC] Implement BuildContext in packages/schemas/docker_compose/build_context.py (context_path, dockerfile, target, args + temporal)

- [X] T063 [P] [P2-DC] Write test for DeviceMapping in tests/packages/schemas/docker_compose/test_device_mapping.py
- [X] T064 [P] [P2-DC] Implement DeviceMapping in packages/schemas/docker_compose/device_mapping.py (host_device, container_device, permissions + temporal)

### Agent 2: SWAG Entities (6 models)

- [X] T065 [P] [P2-SW] Write test for SwagConfigFile in tests/packages/schemas/swag/test_swag_config_file.py
- [X] T066 [P] [P2-SW] Implement SwagConfigFile in packages/schemas/swag/swag_config_file.py (file_path, version, parsed_at + temporal)

- [X] T067 [P] [P2-SW] Write test for Proxy in tests/packages/schemas/swag/test_proxy.py
- [X] T068 [P] [P2-SW] Implement Proxy in packages/schemas/swag/proxy.py (name, proxy_type, config_path + temporal)

- [X] T069 [P] [P2-SW] Write test for ProxyRoute in tests/packages/schemas/swag/test_proxy_route.py
- [X] T070 [P] [P2-SW] Implement ProxyRoute in packages/schemas/swag/proxy_route.py (server_name, upstream_app, upstream_port, upstream_proto, tls_enabled + temporal)

- [X] T071 [P] [P2-SW] Write test for LocationBlock in tests/packages/schemas/swag/test_location_block.py
- [X] T072 [P] [P2-SW] Implement LocationBlock in packages/schemas/swag/location_block.py (path, proxy_pass_url, auth_enabled, auth_type + temporal)

- [X] T073 [P] [P2-SW] Write test for UpstreamConfig in tests/packages/schemas/swag/test_upstream_config.py
- [X] T074 [P] [P2-SW] Implement UpstreamConfig in packages/schemas/swag/upstream_config.py (app, port, proto + temporal)

- [X] T075 [P] [P2-SW] Write test for ProxyHeader in tests/packages/schemas/swag/test_proxy_header.py
- [X] T076 [P] [P2-SW] Implement ProxyHeader in packages/schemas/swag/proxy_header.py (header_name, header_value, header_type + temporal)

### Agent 3: GitHub Entities (12 models) ✅ COMPLETE

- [X] T077 [P] [P2-GH] Write test for Repository in tests/packages/schemas/github/test_repository.py ✅
- [X] T078 [P] [P2-GH] Implement Repository in packages/schemas/github/repository.py (owner, name, full_name, url, default_branch, description, language, stars, forks, open_issues, is_private, is_fork + temporal) ✅

- [X] T079 [P] [P2-GH] Write test for Issue in tests/packages/schemas/github/test_issue.py ✅
- [X] T080 [P] [P2-GH] Implement Issue in packages/schemas/github/issue.py (number, title, state, body, author_login, created_at, closed_at, comments_count + temporal) ✅

- [X] T081 [P] [P2-GH] Write test for PullRequest in tests/packages/schemas/github/test_pull_request.py ✅
- [X] T082 [P] [P2-GH] Implement PullRequest in packages/schemas/github/pull_request.py (number, title, state, base_branch, head_branch, merged, merged_at, commits, additions, deletions + temporal) ✅

- [X] T083 [P] [P2-GH] Write test for Commit in tests/packages/schemas/github/test_commit.py ✅
- [X] T084 [P] [P2-GH] Implement Commit in packages/schemas/github/commit.py (sha, message, author_login, author_name, author_email, timestamp, tree_sha, parent_shas, additions, deletions + temporal) ✅

- [X] T085 [P] [P2-GH] Write test for Branch in tests/packages/schemas/github/test_branch.py ✅
- [X] T086 [P] [P2-GH] Implement Branch in packages/schemas/github/branch.py (name, protected, sha, ref + temporal) ✅

- [X] T087 [P] [P2-GH] Write test for Tag in tests/packages/schemas/github/test_tag.py ✅
- [X] T088 [P] [P2-GH] Implement Tag in packages/schemas/github/tag.py (name, sha, ref, message, tagger + temporal) ✅

- [X] T089 [P] [P2-GH] Write test for GitHubLabel in tests/packages/schemas/github/test_github_label.py ✅
- [X] T090 [P] [P2-GH] Implement GitHubLabel in packages/schemas/github/github_label.py (name, color, description + temporal) ✅

- [X] T091 [P] [P2-GH] Write test for Milestone in tests/packages/schemas/github/test_milestone.py ✅
- [X] T092 [P] [P2-GH] Implement Milestone in packages/schemas/github/milestone.py (number, title, state, due_on, description + temporal) ✅

- [X] T093 [P] [P2-GH] Write test for Comment in tests/packages/schemas/github/test_comment.py ✅
- [X] T094 [P] [P2-GH] Implement Comment in packages/schemas/github/comment.py (id, author_login, body, created_at, updated_at + temporal) ✅

- [X] T095 [P] [P2-GH] Write test for Release in tests/packages/schemas/github/test_release.py ✅
- [X] T096 [P] [P2-GH] Implement Release in packages/schemas/github/release.py (tag_name, name, body, draft, prerelease, created_at, published_at, tarball_url, zipball_url + temporal) ✅

- [X] T097 [P] [P2-GH] Write test for Documentation in tests/packages/schemas/github/test_documentation.py ✅
- [X] T098 [P] [P2-GH] Implement Documentation in packages/schemas/github/documentation.py (file_path, content, format, title + temporal) ✅

- [X] T099 [P] [P2-GH] Write test for BinaryAsset in tests/packages/schemas/github/test_binary_asset.py ✅
- [X] T100 [P] [P2-GH] Implement BinaryAsset in packages/schemas/github/binary_asset.py (file_path, size, mime_type, download_url + temporal) ✅

### Agent 4: Gmail Entities (4 models)

- [X] T101 [P] [P2-GM] Write test for Email in tests/packages/schemas/gmail/test_email.py
- [X] T102 [P] [P2-GM] Implement Email in packages/schemas/gmail/email.py (message_id, thread_id, subject, snippet, body, sent_at, labels, size_estimate, has_attachments, in_reply_to, references + temporal)

- [X] T103 [P] [P2-GM] Write test for Thread in tests/packages/schemas/gmail/test_thread.py
- [X] T104 [P] [P2-GM] Implement Thread in packages/schemas/gmail/thread.py (thread_id, subject, message_count, participant_count, first_message_at, last_message_at, labels + temporal)

- [X] T105 [P] [P2-GM] Write test for GmailLabel in tests/packages/schemas/gmail/test_gmail_label.py
- [X] T106 [P] [P2-GM] Implement GmailLabel in packages/schemas/gmail/gmail_label.py (label_id, name, type, color, message_count + temporal)

- [X] T107 [P] [P2-GM] Write test for Attachment in tests/packages/schemas/gmail/test_attachment.py
- [X] T108 [P] [P2-GM] Implement Attachment in packages/schemas/gmail/attachment.py (attachment_id, filename, mime_type, size, content_hash, is_inline + temporal)

### Agent 5: Reddit Entities (3 models)

- [X] T109 [P] [P2-RD] Write test for Subreddit in tests/packages/schemas/reddit/test_subreddit.py
- [X] T110 [P] [P2-RD] Implement Subreddit in packages/schemas/reddit/subreddit.py (name, display_name, description, subscribers, created_utc, over_18 + temporal)

- [X] T111 [P] [P2-RD] Write test for RedditPost in tests/packages/schemas/reddit/test_reddit_post.py
- [X] T112 [P] [P2-RD] Implement RedditPost in packages/schemas/reddit/reddit_post.py (post_id, title, selftext, score, num_comments, created_utc, url, permalink, is_self, over_18, gilded + temporal)

- [X] T113 [P] [P2-RD] Write test for RedditComment in tests/packages/schemas/reddit/test_reddit_comment.py
- [X] T114 [P] [P2-RD] Implement RedditComment in packages/schemas/reddit/reddit_comment.py (comment_id, body, score, created_utc, permalink, parent_id, depth, gilded, edited + temporal)

### Agent 6: YouTube Entities (3 models)

- [X] T115 [P] [P2-YT] Write test for Video in tests/packages/schemas/youtube/test_video.py
- [X] T116 [P] [P2-YT] Implement Video in packages/schemas/youtube/video.py (video_id, title, url, duration, views, published_at, description, language + temporal)

- [X] T117 [P] [P2-YT] Write test for Channel in tests/packages/schemas/youtube/test_channel.py
- [X] T118 [P] [P2-YT] Implement Channel in packages/schemas/youtube/channel.py (channel_id, channel_name, channel_url, subscribers, verified + temporal)

- [X] T119 [P] [P2-YT] Write test for Transcript in tests/packages/schemas/youtube/test_transcript.py
- [X] T120 [P] [P2-YT] Implement Transcript in packages/schemas/youtube/transcript.py (transcript_id, video_id, language, auto_generated, content + temporal)

### Agent 7: Tailscale Entities (3 models)

- [X] T121 [P] [P2-TS] Write test for TailscaleDevice in tests/packages/schemas/tailscale/test_tailscale_device.py
- [X] T122 [P] [P2-TS] Implement TailscaleDevice in packages/schemas/tailscale/tailscale_device.py (device_id, hostname, os, ipv4_address, ipv6_address, endpoints, key_expiry, is_exit_node, subnet_routes, ssh_enabled, tailnet_dns_name + temporal)

- [X] T123 [P] [P2-TS] Write test for TailscaleNetwork in tests/packages/schemas/tailscale/test_tailscale_network.py
- [X] T124 [P] [P2-TS] Implement TailscaleNetwork in packages/schemas/tailscale/tailscale_network.py (network_id, name, cidr, global_nameservers, search_domains + temporal)

- [X] T125 [P] [P2-TS] Write test for TailscaleACL in tests/packages/schemas/tailscale/test_tailscale_acl.py
- [X] T126 [P] [P2-TS] Implement TailscaleACL in packages/schemas/tailscale/tailscale_acl.py (rule_id, action, source_tags, destination_tags, ports + temporal)

### Agent 8: Unifi Entities (9 models) ✅ COMPLETE

- [X] T127 [P] [P2-UF] Write test for UnifiDevice in tests/packages/schemas/unifi/test_unifi_device.py
- [X] T128 [P] [P2-UF] Implement UnifiDevice in packages/schemas/unifi/unifi_device.py (mac, hostname, type, model, adopted, state, ip, firmware_version, link_speed, connection_type, uptime + temporal)

- [X] T129 [P] [P2-UF] Write test for UnifiClient in tests/packages/schemas/unifi/test_unifi_client.py
- [X] T130 [P] [P2-UF] Implement UnifiClient in packages/schemas/unifi/unifi_client.py (mac, hostname, ip, network, is_wired, link_speed, connection_type, uptime + temporal)

- [X] T131 [P] [P2-UF] Write test for UnifiNetwork in tests/packages/schemas/unifi/test_unifi_network.py
- [X] T132 [P] [P2-UF] Implement UnifiNetwork in packages/schemas/unifi/unifi_network.py (network_id, name, vlan_id, subnet, gateway_ip, dns_servers, wifi_name + temporal)

- [X] T133 [P] [P2-UF] Write test for UnifiSite in tests/packages/schemas/unifi/test_unifi_site.py
- [X] T134 [P] [P2-UF] Implement UnifiSite in packages/schemas/unifi/unifi_site.py (site_id, name, description, wan_ip, gateway_ip, dns_servers + temporal)

- [X] T135 [P] [P2-UF] Write test for PortForwardingRule in tests/packages/schemas/unifi/test_port_forwarding_rule.py
- [X] T136 [P] [P2-UF] Implement PortForwardingRule in packages/schemas/unifi/port_forwarding_rule.py (rule_id, name, enabled, proto, src, dst_port, fwd, fwd_port, pfwd_interface + temporal)

- [X] T137 [P] [P2-UF] Write test for FirewallRule in tests/packages/schemas/unifi/test_firewall_rule.py
- [X] T138 [P] [P2-UF] Implement FirewallRule in packages/schemas/unifi/firewall_rule.py (rule_id, name, enabled, action, protocol, ip_version, index, source_zone, dest_zone, logging + temporal)

- [X] T139 [P] [P2-UF] Write test for TrafficRule in tests/packages/schemas/unifi/test_traffic_rule.py
- [X] T140 [P] [P2-UF] Implement TrafficRule in packages/schemas/unifi/traffic_rule.py (rule_id, name, enabled, action, bandwidth_limit, matching_target, ip_addresses, domains, schedule + temporal)

- [X] T141 [P] [P2-UF] Write test for TrafficRoute in tests/packages/schemas/unifi/test_traffic_route.py
- [X] T142 [P] [P2-UF] Implement TrafficRoute in packages/schemas/unifi/traffic_route.py (route_id, name, enabled, next_hop, matching_target, network_id, ip_addresses, domains + temporal)

- [X] T143 [P] [P2-UF] Write test for NATRule in tests/packages/schemas/unifi/test_nat_rule.py
- [X] T144 [P] [P2-UF] Implement NATRule in packages/schemas/unifi/nat_rule.py (rule_id, name, enabled, type, source, destination + temporal)

### Web/Elasticsearch Entity (1 model) ✅ COMPLETE

- [X] T145 [P] [P2-WEB] Write test for Document in tests/packages/schemas/web/test_document.py ✅
- [X] T146 [P] [P2-WEB] Implement Document in packages/schemas/web/document.py (doc_id, source_url, source_type, content_hash, ingested_at, extraction_state + temporal) ✅

**Checkpoint**: All 53 reader-specific entities complete, all tests green

---

## Phase 3: Graph Writers (TDD, Parallel, 6-8h wall-clock)

**Goal**: Implement 15 graph writers following SwagGraphWriter pattern (2000-row UNWIND batches).

**Agents**: 10 programmers (2 handle multiple writers)

**Agent Assignment**:
- **Agent 1**: PersonWriter + OrganizationWriter
- **Agent 2**: PlaceWriter + EventWriter + FileWriter
- **Agent 3**: DockerComposeWriter
- **Agent 4**: SwagWriter (update existing)
- **Agent 5**: GitHubWriter
- **Agent 6**: GmailWriter
- **Agent 7**: RedditWriter + YouTubeWriter
- **Agent 8**: TailscaleWriter
- **Agent 9**: UnifiWriter
- **Agent 10**: DocumentWriter + RelationshipWriter

**TDD Pattern**:
```
For each writer:
1. Write failing test (empty list, single entity, batch 2000, idempotent, constraint violations)
2. Implement writer following SwagGraphWriter pattern (2000-row UNWIND batches)
3. Refactor
4. Verify ≥95% coverage
```

**Completion Criteria (per agent)**:
- [ ] All writer tests pass
- [ ] Coverage ≥95%
- [ ] Performance: ≥20k edges/min
- [ ] Progress checkboxes marked

### Agent 1: Core Writers (Person, Organization) ✅ COMPLETE

- [X] T147 [P] [P3-CORE] Write test for PersonWriter in tests/packages/graph/writers/test_person_writer.py (empty list, single, batch 2000, idempotent) ✅
- [X] T148 [P] [P3-CORE] Implement PersonWriter in packages/graph/writers/person_writer.py (2000-row UNWIND batches, temporal tracking) ✅
- [X] T149 [P] [P3-CORE] Refactor PersonWriter (optimize Cypher, add error handling) ✅

- [X] T150 [P] [P3-CORE] Write test for OrganizationWriter in tests/packages/graph/writers/test_organization_writer.py ✅
- [X] T151 [P] [P3-CORE] Implement OrganizationWriter in packages/graph/writers/organization_writer.py ✅
- [X] T152 [P] [P3-CORE] Refactor OrganizationWriter ✅

### Agent 2: Core Writers (Place, Event, File)

- [X] T153 [P] [P3-CORE2] Write test for PlaceWriter in tests/packages/graph/writers/test_place_writer.py
- [X] T154 [P] [P3-CORE2] Implement PlaceWriter in packages/graph/writers/place_writer.py
- [X] T155 [P] [P3-CORE2] Refactor PlaceWriter

- [X] T156 [P] [P3-CORE2] Write test for EventWriter in tests/packages/graph/writers/test_event_writer.py
- [X] T157 [P] [P3-CORE2] Implement EventWriter in packages/graph/writers/event_writer.py
- [X] T158 [P] [P3-CORE2] Refactor EventWriter

- [X] T159 [P] [P3-CORE2] Write test for FileWriter in tests/packages/graph/writers/test_file_writer.py
- [X] T160 [P] [P3-CORE2] Implement FileWriter in packages/graph/writers/file_writer.py
- [X] T161 [P] [P3-CORE2] Refactor FileWriter

### Agent 3: Docker Compose Writer

- [X] T162 [P] [P3-DC] Write test for DockerComposeWriter in tests/packages/graph/writers/test_docker_compose_writer.py (all 12 entity types, relationships)
- [X] T163 [P] [P3-DC] Implement DockerComposeWriter in packages/graph/writers/docker_compose_writer.py (ComposeFile, ComposeProject, ComposeService, ComposeNetwork, ComposeVolume, PortBinding, EnvironmentVariable, ServiceDependency, ImageDetails, HealthCheck, BuildContext, DeviceMapping)
- [X] T164 [P] [P3-DC] Refactor DockerComposeWriter (optimize multi-entity batching)

### Agent 4: SWAG Writer (Update Existing)

- [X] T165 [P] [P3-SW] Update tests in tests/packages/graph/writers/test_swag_writer.py for new entity types (SwagConfigFile, Proxy, ProxyRoute, LocationBlock, UpstreamConfig, ProxyHeader)
- [X] T166 [P] [P3-SW] Update packages/graph/writers/swag_writer.py to use new SWAG entities
- [X] T167 [P] [P3-SW] Refactor SwagWriter for new relationship types

### Agent 5: GitHub Writer ✅ COMPLETE

- [X] T168 [P] [P3-GH] Write test for GitHubWriter in tests/packages/graph/writers/test_github_writer.py (all 12 entity types, relationships) ✅
- [X] T169 [P] [P3-GH] Implement GitHubWriter in packages/graph/writers/github_writer.py (Repository, Issue, PullRequest, Commit, Branch, Tag, GitHubLabel, Milestone, Comment, Release, Documentation, BinaryAsset) ✅
- [X] T170 [P] [P3-GH] Refactor GitHubWriter ✅

### Agent 6: Gmail Writer

- [X] T171 [P] [P3-GM] Write test for GmailWriter in tests/packages/graph/writers/test_gmail_writer.py (Email, Thread, GmailLabel, Attachment, relationships)
- [X] T172 [P] [P3-GM] Implement GmailWriter in packages/graph/writers/gmail_writer.py
- [X] T173 [P] [P3-GM] Refactor GmailWriter

### Agent 7: Reddit + YouTube Writers

- [X] T174 [P] [P3-RD] Write test for RedditWriter in tests/packages/graph/writers/test_reddit_writer.py
- [X] T175 [P] [P3-RD] Implement RedditWriter in packages/graph/writers/reddit_writer.py (Subreddit, RedditPost, RedditComment, relationships)
- [X] T176 [P] [P3-RD] Refactor RedditWriter

- [X] T177 [P] [P3-YT] Write test for YouTubeWriter in tests/packages/graph/writers/test_youtube_writer.py
- [X] T178 [P] [P3-YT] Implement YouTubeWriter in packages/graph/writers/youtube_writer.py (Video, Channel, Transcript, relationships)
- [X] T179 [P] [P3-YT] Refactor YouTubeWriter

### Agent 8: Tailscale Writer

- [X] T180 [P] [P3-TS] Write test for TailscaleWriter in tests/packages/graph/writers/test_tailscale_writer.py
- [X] T181 [P] [P3-TS] Implement TailscaleWriter in packages/graph/writers/tailscale_writer.py (TailscaleDevice, TailscaleNetwork, TailscaleACL, relationships)
- [X] T182 [P] [P3-TS] Refactor TailscaleWriter

### Agent 9: Unifi Writer

- [X] T183 [P] [P3-UF] Write test for UnifiWriter in tests/packages/graph/writers/test_unifi_writer.py (all 9 entity types, relationships)
- [X] T184 [P] [P3-UF] Implement UnifiWriter in packages/graph/writers/unifi_writer.py (UnifiDevice, UnifiClient, UnifiNetwork, UnifiSite, PortForwardingRule, FirewallRule, TrafficRule, TrafficRoute, NATRule)
- [X] T185 [P] [P3-UF] Refactor UnifiWriter

### Agent 10: Document + Relationship Writers ✅ COMPLETE

- [X] T186 [P] [P3-DOC] Write test for DocumentWriter in tests/packages/graph/writers/test_document_writer.py ✅
- [X] T187 [P] [P3-DOC] Implement DocumentWriter in packages/graph/writers/document_writer.py (Document entity, MENTIONS relationships) ✅
- [X] T188 [P] [P3-DOC] Refactor DocumentWriter ✅

- [X] T189 [P] [P3-REL] Write test for RelationshipWriter in tests/packages/graph/writers/test_relationship_writer.py (all 10 core relationship types) ✅
- [X] T190 [P] [P3-REL] Implement RelationshipWriter in packages/graph/writers/relationship_writer.py (generic writer for all Pydantic relationship schemas) ✅
- [X] T191 [P] [P3-REL] Refactor RelationshipWriter ✅

**Checkpoint**: All 15 writers complete, all tests green, coverage ≥95%

---

## Phase 4: Reader Updates (TDD, Parallel, 4-6h wall-clock)

**Goal**: Update all readers to output new entity types.

**Agents**: 8 programmers

**Agent Assignment**:
- **Agent 1**: docker_compose reader
- **Agent 2**: swag reader
- **Agent 3**: github reader
- **Agent 4**: gmail reader
- **Agent 5**: reddit reader
- **Agent 6**: youtube reader
- **Agent 7**: tailscale reader
- **Agent 8**: unifi reader

**TDD Pattern**:
```
For each reader:
1. Write failing integration test (read source → extract entities)
2. Update reader to output new entity types
3. Refactor
```

**Completion Criteria (per agent)**:
- [ ] Reader outputs new entity types
- [ ] Integration test passes

### Agent 1: Docker Compose Reader

- [X] T192 [P] [P4-DC] Write integration test for DockerComposeReader in tests/packages/ingest/readers/test_docker_compose.py (read compose file → extract all 12 entity types)
- [X] T193 [P] [P4-DC] Update packages/ingest/readers/docker_compose.py to output new entities (ComposeFile, ComposeProject, ComposeService, ComposeNetwork, ComposeVolume, PortBinding, EnvironmentVariable, ServiceDependency, ImageDetails, HealthCheck, BuildContext, DeviceMapping)
- [X] T194 [P] [P4-DC] Refactor DockerComposeReader

### Agent 2: SWAG Reader

- [X] T195 [P] [P4-SW] Write integration test for SwagReader in tests/packages/ingest/readers/test_swag.py
- [X] T196 [P] [P4-SW] Update packages/ingest/readers/swag.py to output new entities (SwagConfigFile, Proxy, ProxyRoute, LocationBlock, UpstreamConfig, ProxyHeader)
- [X] T197 [P] [P4-SW] Refactor SwagReader

### Agent 3: GitHub Reader ✅ COMPLETE

- [X] T198 [P] [P4-GH] Write integration test for GitHubReader in tests/packages/ingest/readers/test_github.py ✅
- [X] T199 [P] [P4-GH] Update packages/ingest/readers/github.py to output new entities (Repository, Issue, PullRequest, Commit, Branch, Tag, GitHubLabel, Milestone, Comment, Release, Documentation, BinaryAsset) ✅
- [X] T200 [P] [P4-GH] Refactor GitHubReader ✅

### Agent 4: Gmail Reader

- [X] T201 [P] [P4-GM] Write integration test for GmailReader in tests/packages/ingest/readers/test_gmail.py
- [X] T202 [P] [P4-GM] Update packages/ingest/readers/gmail.py to output new entities (Email, Thread, GmailLabel, Attachment)
- [X] T203 [P] [P4-GM] Refactor GmailReader

### Agent 5: Reddit Reader

- [X] T204 [P] [P4-RD] Write integration test for RedditReader in tests/packages/ingest/readers/test_reddit.py
- [X] T205 [P] [P4-RD] Update packages/ingest/readers/reddit.py to output new entities (Subreddit, RedditPost, RedditComment)
- [X] T206 [P] [P4-RD] Refactor RedditReader

### Agent 6: YouTube Reader

- [X] T207 [P] [P4-YT] Write integration test for YouTubeReader in tests/packages/ingest/readers/test_youtube.py
- [X] T208 [P] [P4-YT] Update packages/ingest/readers/youtube.py to output new entities (Video, Channel, Transcript)
- [X] T209 [P] [P4-YT] Refactor YouTubeReader

### Agent 7: Tailscale Reader

- [X] T210 [P] [P4-TS] Write integration test for TailscaleReader in tests/packages/ingest/readers/test_tailscale.py
- [X] T211 [P] [P4-TS] Update packages/ingest/readers/tailscale.py to output new entities (TailscaleDevice, TailscaleNetwork, TailscaleACL)
- [X] T212 [P] [P4-TS] Refactor TailscaleReader

### Agent 8: Unifi Reader

- [X] T213 [P] [P4-UF] Write integration test for UnifiReader in tests/packages/ingest/readers/test_unifi.py
- [X] T214 [P] [P4-UF] Update packages/ingest/readers/unifi.py to output new entities (UnifiDevice, UnifiClient, UnifiNetwork, UnifiSite, PortForwardingRule, FirewallRule, TrafficRule, TrafficRoute, NATRule)
- [X] T215 [P] [P4-UF] Refactor UnifiReader

**Checkpoint**: All readers updated, all integration tests green

---

## Phase 5: Use-Case Updates (TDD, Parallel, 4-6h wall-clock)

**Goal**: Update all use-cases to call new writers and use new entity types.

**Agents**: 8 programmers

**Tasks**:
```
For each use-case:
1. Update to call new writers
2. Update to use new entity types
3. Add temporal tracking
4. Verify e2e flow
```

**Completion Criteria (per agent)**:
- [ ] Use-case updated
- [ ] E2E test passes

### Agent 1: Docker Compose Use-Case

- [ ] T216 [P] [P5-DC] Update packages/core/use_cases/ingest_docker_compose.py to call DockerComposeWriter with new entity types
- [ ] T217 [P] [P5-DC] Add temporal tracking (created_at, updated_at, source_timestamp) to all entities
- [ ] T218 [P] [P5-DC] Write e2e test in tests/integration/test_docker_compose_e2e.py
- [ ] T219 [P] [P5-DC] Verify e2e flow passes

### Agent 2: SWAG Use-Case

- [ ] T220 [P] [P5-SW] Update packages/core/use_cases/ingest_swag.py to call SwagWriter with new entity types
- [ ] T221 [P] [P5-SW] Add temporal tracking to all entities
- [ ] T222 [P] [P5-SW] Write e2e test in tests/integration/test_swag_e2e.py
- [ ] T223 [P] [P5-SW] Verify e2e flow passes

### Agent 3: GitHub Use-Case

- [ ] T224 [P] [P5-GH] Update packages/core/use_cases/ingest_github.py to call GitHubWriter with new entity types
- [ ] T225 [P] [P5-GH] Add temporal tracking to all entities
- [ ] T226 [P] [P5-GH] Write e2e test in tests/integration/test_github_e2e.py
- [ ] T227 [P] [P5-GH] Verify e2e flow passes

### Agent 4: Gmail Use-Case

- [ ] T228 [P] [P5-GM] Update packages/core/use_cases/ingest_gmail.py to call GmailWriter with new entity types
- [ ] T229 [P] [P5-GM] Add temporal tracking to all entities
- [ ] T230 [P] [P5-GM] Write e2e test in tests/integration/test_gmail_e2e.py
- [ ] T231 [P] [P5-GM] Verify e2e flow passes

### Agent 5: Reddit Use-Case

- [ ] T232 [P] [P5-RD] Update packages/core/use_cases/ingest_reddit.py to call RedditWriter with new entity types
- [ ] T233 [P] [P5-RD] Add temporal tracking to all entities
- [ ] T234 [P] [P5-RD] Write e2e test in tests/integration/test_reddit_e2e.py
- [ ] T235 [P] [P5-RD] Verify e2e flow passes

### Agent 6: YouTube Use-Case

- [ ] T236 [P] [P5-YT] Update packages/core/use_cases/ingest_youtube.py to call YouTubeWriter with new entity types
- [ ] T237 [P] [P5-YT] Add temporal tracking to all entities
- [ ] T238 [P] [P5-YT] Write e2e test in tests/integration/test_youtube_e2e.py
- [ ] T239 [P] [P5-YT] Verify e2e flow passes

### Agent 7: Tailscale Use-Case

- [ ] T240 [P] [P5-TS] Update packages/core/use_cases/ingest_tailscale.py to call TailscaleWriter with new entity types
- [ ] T241 [P] [P5-TS] Add temporal tracking to all entities
- [ ] T242 [P] [P5-TS] Write e2e test in tests/integration/test_tailscale_e2e.py
- [ ] T243 [P] [P5-TS] Verify e2e flow passes

### Agent 8: Unifi Use-Case

- [ ] T244 [P] [P5-UF] Update packages/core/use_cases/ingest_unifi.py to call UnifiWriter with new entity types
- [ ] T245 [P] [P5-UF] Add temporal tracking to all entities
- [ ] T246 [P] [P5-UF] Write e2e test in tests/integration/test_unifi_e2e.py
- [ ] T247 [P] [P5-UF] Verify e2e flow passes

**Checkpoint**: All use-cases updated, all e2e tests green

---

## Phase 6: Verification (Parallel, 2-3h wall-clock)

**Goal**: Comprehensive verification before sign-off.

**Agents**: 10 verification agents

**Verification Checklist**:
- [ ] All deleted files removed (Service, Host, IP, old Proxy, Endpoint, BatchedGraphWriter, legacy tests)
- [ ] All updated files modified correctly (SwagWriter, __init__.py exports, constraint count)
- [ ] All created files exist (58 schemas, 15 writers, 37 tests)
- [ ] Unit tests: 100% pass
- [ ] Integration tests: 100% pass
- [ ] Neo4j constraints: 58 total (SHOW CONSTRAINTS)
- [ ] Performance: ≥20k edges/min
- [ ] Coverage: ≥95% writers
- [ ] E2E smoke tests pass
- [ ] Docs updated

### Agent 1: File Deletion Verification

- [ ] T248 [P] [P6-VER] Verify deleted schemas: packages/schemas/models/__init__.py (Service, Host, IP, old Proxy, Endpoint lines removed)
- [ ] T249 [P] [P6-VER] Verify deleted writers: packages/graph/writers/batched.py removed
- [ ] T250 [P] [P6-VER] Verify deleted tests: tests/packages/schemas/test_graph_nodes.py removed
- [ ] T251 [P] [P6-VER] Verify deleted tests: tests/packages/schemas/test_extraction_job.py removed
- [ ] T252 [P] [P6-VER] Verify deleted tests: tests/packages/schemas/test_extraction_window.py removed
- [ ] T253 [P] [P6-VER] Verify deleted tests: tests/packages/graph/test_writers.py removed
- [ ] T254 [P] [P6-VER] Verify deleted tests: tests/integration/test_ingest_creates_document_records.py removed

### Agent 2: File Update Verification

- [ ] T255 [P] [P6-VER] Verify packages/graph/writers/__init__.py exports updated for new writers
- [ ] T256 [P] [P6-VER] Verify packages/schemas/__init__.py exports updated for new entities
- [ ] T257 [P] [P6-VER] Verify tests/packages/graph/test_constraints.py constraint count updated to 58

### Agent 3: File Creation Verification

- [ ] T258 [P] [P6-VER] Verify all 58 schema files exist (5 core + 53 reader-specific)
- [ ] T259 [P] [P6-VER] Verify all 15 writer files exist
- [ ] T260 [P] [P6-VER] Verify all 37 test files exist (10 schema tests + 15 writer tests + 9 integration tests + 3 use-case tests)

### Agent 4: Unit Test Verification

- [ ] T261 [P] [P6-VER] Run unit tests for core schemas: `uv run pytest tests/packages/schemas/core/ -v`
- [ ] T262 [P] [P6-VER] Run unit tests for reader-specific schemas: `uv run pytest tests/packages/schemas/{docker_compose,swag,github,gmail,reddit,youtube,tailscale,unifi,web}/ -v`
- [ ] T263 [P] [P6-VER] Run unit tests for relationship schemas: `uv run pytest tests/packages/schemas/relationships/ -v`
- [ ] T264 [P] [P6-VER] Run unit tests for graph writers: `uv run pytest tests/packages/graph/writers/ -v`
- [ ] T265 [P] [P6-VER] Verify 100% pass rate

### Agent 5: Integration Test Verification

- [ ] T266 [P] [P6-VER] Run integration tests for readers: `uv run pytest tests/packages/ingest/readers/ -m integration -v`
- [ ] T267 [P] [P6-VER] Run integration tests for use-cases: `uv run pytest tests/packages/core/use_cases/ -m integration -v`
- [ ] T268 [P] [P6-VER] Run e2e integration tests: `uv run pytest tests/integration/ -v`
- [ ] T269 [P] [P6-VER] Verify 100% pass rate

### Agent 6: Neo4j Constraint Verification

- [ ] T270 [P] [P6-VER] Wipe Neo4j database: `docker volume rm taboot_neo4j_data && docker compose up -d taboot-graph`
- [ ] T271 [P] [P6-VER] Run init: `uv run apps/cli init`
- [ ] T272 [P] [P6-VER] Query constraints: Run `SHOW CONSTRAINTS` in Neo4j and verify exactly 58 constraints exist
- [ ] T273 [P] [P6-VER] Verify constraint names match new entity types (Person, Organization, Place, Event, File, ComposeFile, etc.)

### Agent 7: Performance Verification

- [ ] T274 [P] [P6-VER] Benchmark DockerComposeWriter throughput (≥20k edges/min)
- [ ] T275 [P] [P6-VER] Benchmark SwagWriter throughput (≥20k edges/min)
- [ ] T276 [P] [P6-VER] Benchmark GitHubWriter throughput (≥20k edges/min)
- [ ] T277 [P] [P6-VER] Verify all writers meet ≥20k edges/min threshold

### Agent 8: Coverage Verification

- [ ] T278 [P] [P6-VER] Run coverage for graph writers: `uv run pytest --cov=packages/graph/writers tests/packages/graph/writers/`
- [ ] T279 [P] [P6-VER] Verify coverage ≥95% for all writers
- [ ] T280 [P] [P6-VER] Generate coverage report: `uv run pytest --cov-report=html`

### Agent 9: E2E Smoke Tests

- [ ] T281 [P] [P6-VER] Smoke test: Docker Compose ingestion (`uv run apps/cli ingest docker-compose docker-compose.yaml`)
- [ ] T282 [P] [P6-VER] Smoke test: SWAG ingestion (`uv run apps/cli ingest swag /path/to/swag/config`)
- [ ] T283 [P] [P6-VER] Smoke test: GitHub ingestion (`uv run apps/cli ingest github anthropics/claude-code`)
- [ ] T284 [P] [P6-VER] Smoke test: Query new entities (`uv run apps/cli graph query "MATCH (p:Person) RETURN p LIMIT 10"`)
- [ ] T285 [P] [P6-VER] Verify all smoke tests pass

### Agent 10: Documentation Verification

- [ ] T286 [P] [P6-VER] Update CLAUDE.md with new entity model (remove Service, Host, IP; add Person, Organization, Place, Event, File + 53 reader-specific)
- [ ] T287 [P] [P6-VER] Update NEO4J_REFACTOR.md status to "COMPLETE"
- [ ] T288 [P] [P6-VER] Update docs/NEO4J_COURSE_CORRECTION.md with final entity counts and implementation notes
- [ ] T289 [P] [P6-VER] Verify all documentation references updated

**Checkpoint**: All verification checks pass

---

## Success Metrics

### Functional Completeness
- [ ] 5 core + 53 reader-specific entities = 58 total ✓
- [ ] All entities have temporal tracking ✓
- [ ] All relationships have Pydantic schemas ✓
- [ ] All 15 writers implement write_* methods ✓
- [ ] All 10 readers output new entity types ✓
- [ ] Neo4j constraints: 58 total ✓

### Test Coverage
- [ ] Unit tests: <10s total ✓
- [ ] Integration tests: <2min total ✓
- [ ] Coverage: ≥95% for packages/graph/writers/ ✓
- [ ] All TDD cycles complete (red → green → refactor) ✓

### Performance
- [ ] Writer throughput: ≥20k edges/min (333 edges/sec) ✓
- [ ] Neo4j UNWIND batches: 2000 rows ✓
- [ ] Extraction: ≥50 pages/sec (Tier A) ✓

---

## Parallelization Summary

**Phase 1 (Core Schemas)**: Sequential (1 agent) - 12-14h
**Phase 2 (Reader Schemas)**: 8 parallel agents - 8-10h wall-clock
**Phase 3 (Graph Writers)**: 10 parallel agents - 6-8h wall-clock
**Phase 4 (Reader Updates)**: 8 parallel agents - 4-6h wall-clock
**Phase 5 (Use-Case Updates)**: 8 parallel agents - 4-6h wall-clock
**Phase 6 (Verification)**: 10 parallel agents - 2-3h wall-clock

**Total Wall-Clock Time**: 36-47 hours
**Total Agent-Hours**: ~180 hours (with parallelization)

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

2. **Parallel agent coordination**
   - Mitigation: Phase gates enforce completion before proceeding
   - Mitigation: Progress checkboxes tracked by each agent

### Medium Severity
3. **Test data cleanup**
   - Mitigation: Pytest fixtures with teardown
   - Mitigation: `MATCH (n) DETACH DELETE n` after each test

4. **Performance degradation**
   - Mitigation: Benchmark before/after, <20% overhead acceptable
   - Mitigation: Each constraint adds ~10-15% write overhead

---

## Next Steps

1. ✅ Review this tasks.md document
2. ✅ Execute Phase 1 (core schemas) - Sequential
3. ⏳ Execute Phase 2 (reader-specific schemas) - 8 parallel agents (next focus)
4. ⏳ Execute Phase 3 (graph writers) - 10 parallel agents
5. ⏳ Execute Phase 4 (reader updates) - 8 parallel agents
6. ⏳ Execute Phase 5 (use-case updates) - 8 parallel agents
7. ⏳ Execute Phase 6 (verification) - 10 parallel agents
8. ⏳ Sign-off and merge

**Estimated Total Time**: 50-60 hours wall-clock with aggressive parallelization

---

**Document Status**: Implementation Ready
**Last Updated**: 2025-10-28
**Next Action**: Begin Phase 1 (Core Schemas) with sequential TDD approach
