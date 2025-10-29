# Neo4j Task Verification

## Batch 1 (Tasks 1-10)
- R001: Not implemented — no Unifi research artifact in docs/investigations.
- R002: Not implemented — no evidence of research completion in docs/investigations.
- R003 (NEO4J_REFACTOR.md): Implemented.
- R004: Not implemented — missing file manifest under docs/ or plans/.
- R005 (tests/packages/schemas/core/): Implemented.
- T001 (tests/packages/schemas/core/test_person.py): Implemented.
- T002 (packages/schemas/core/person.py): Implemented.
- T003 (packages/schemas/core/person.py): Implemented.
- T004 (tests/packages/schemas/core/test_organization.py): Implemented.
- T005 (packages/schemas/core/organization.py): Implemented.

## Batch 2 (Tasks 11-20)
- T006 (packages/schemas/core/organization.py): Implemented.
- T007 (tests/packages/schemas/core/test_place.py): Implemented.
- T008 (packages/schemas/core/place.py): Implemented.
- T009 (packages/schemas/core/place.py): Implemented.
- T010 (tests/packages/schemas/core/test_event.py): Implemented.
- T011 (packages/schemas/core/event.py): Implemented.
- T012 (packages/schemas/core/event.py): Implemented.
- T013 (tests/packages/schemas/core/test_file.py): Implemented.
- T014 (packages/schemas/core/file.py): Implemented.
- T015 (packages/schemas/core/file.py): Implemented.

## Batch 3 (Tasks 21-30)
- T016 (tests/packages/schemas/relationships/test_base_relationship.py): Implemented.
- T017 (packages/schemas/relationships/base.py): Implemented.
- T018 (packages/schemas/relationships/base.py): Implemented.
- T019 (tests/packages/schemas/relationships/test_mentions_relationship.py): Implemented.
- T020 (packages/schemas/relationships/mentions.py): Implemented.
- T021 (tests/packages/schemas/relationships/test_works_at.py): Implemented.
- T022 (packages/schemas/relationships/works_at.py): Implemented.
- T023 (tests/packages/schemas/relationships/test_routes_to.py): Implemented.
- T024 (packages/schemas/relationships/routes_to.py): Implemented.
- T025 (tests/packages/schemas/relationships/test_depends_on.py): Implemented.

## Batch 4 (Tasks 31-40)
- T026 (packages/schemas/relationships/depends_on.py): Implemented.
- T027 (tests/packages/schemas/relationships/test_sent.py): Implemented.
- T028 (packages/schemas/relationships/sent.py): Implemented.
- T029 (tests/packages/schemas/relationships/test_contributes_to.py): Implemented.
- T030 (packages/schemas/relationships/contributes_to.py): Implemented.
- T031 (tests/packages/schemas/relationships/test_created.py): Implemented.
- T032 (packages/schemas/relationships/created.py): Implemented.
- T033 (tests/packages/schemas/relationships/test_belongs_to.py): Implemented.
- T034 (packages/schemas/relationships/belongs_to.py): Implemented.
- T035 (tests/packages/schemas/relationships/test_in_thread.py): Implemented.

## Batch 5 (Tasks 41-50)
- T036 (packages/schemas/relationships/in_thread.py): Implemented.
- T037 (tests/packages/schemas/relationships/test_located_in.py): Implemented.
- T038 (packages/schemas/relationships/located_in.py): Implemented.
- T039 (specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher): Implemented.
- T040: Not implemented — no evidence of `SHOW CONSTRAINTS` verification (tests/integration/test_init_e2e.py still checks legacy constraints).
- T041 (tests/packages/schemas/docker_compose/test_compose_file.py): Implemented.
- T042 (packages/schemas/docker_compose/compose_file.py): Implemented.
- T043 (tests/packages/schemas/docker_compose/test_compose_project.py): Implemented.
- T044 (packages/schemas/docker_compose/compose_project.py): Implemented.
- T045 (tests/packages/schemas/docker_compose/test_compose_service.py): Implemented.

## Batch 6 (Tasks 51-60)
- T046 (packages/schemas/docker_compose/compose_service.py): Implemented.
- T047 (tests/packages/schemas/docker_compose/test_compose_network.py): Implemented.
- T048 (packages/schemas/docker_compose/compose_network.py): Implemented.
- T049 (tests/packages/schemas/docker_compose/test_compose_volume.py): Implemented.
- T050 (packages/schemas/docker_compose/compose_volume.py): Implemented.
- T051 (tests/packages/schemas/docker_compose/test_port_binding.py): Implemented.
- T052 (packages/schemas/docker_compose/port_binding.py): Implemented.
- T053 (tests/packages/schemas/docker_compose/test_environment_variable.py): Implemented.
- T054 (packages/schemas/docker_compose/environment_variable.py): Implemented.
- T055 (tests/packages/schemas/docker_compose/test_service_dependency.py): Implemented.

## Batch 7 (Tasks 61-70)
- T056 (packages/schemas/docker_compose/service_dependency.py): Implemented.
- T057 (tests/packages/schemas/docker_compose/test_image_details.py): Implemented.
- T058 (packages/schemas/docker_compose/image_details.py): Implemented.
- T059 (tests/packages/schemas/docker_compose/test_health_check.py): Implemented.
- T060 (packages/schemas/docker_compose/health_check.py): Implemented.
- T061 (tests/packages/schemas/docker_compose/test_build_context.py): Implemented.
- T062 (packages/schemas/docker_compose/build_context.py): Implemented.
- T063 (tests/packages/schemas/docker_compose/test_device_mapping.py): Implemented.
- T064 (packages/schemas/docker_compose/device_mapping.py): Implemented.
- T065 (tests/packages/schemas/swag/test_swag_config_file.py): Implemented.

## Batch 8 (Tasks 71-80)
- T066 (packages/schemas/swag/swag_config_file.py): Implemented.
- T067 (tests/packages/schemas/swag/test_proxy.py): Implemented.
- T068 (packages/schemas/swag/proxy.py): Implemented.
- T069 (tests/packages/schemas/swag/test_proxy_route.py): Implemented.
- T070 (packages/schemas/swag/proxy_route.py): Implemented.
- T071 (tests/packages/schemas/swag/test_location_block.py): Implemented.
- T072 (packages/schemas/swag/location_block.py): Implemented.
- T073 (tests/packages/schemas/swag/test_upstream_config.py): Implemented.
- T074 (packages/schemas/swag/upstream_config.py): Implemented.
- T075 (tests/packages/schemas/swag/test_proxy_header.py): Implemented.

## Batch 9 (Tasks 81-90)
- T076 (packages/schemas/swag/proxy_header.py): Implemented.
- T077 (tests/packages/schemas/github/test_repository.py): Implemented.
- T078 (packages/schemas/github/repository.py): Implemented.
- T079 (tests/packages/schemas/github/test_issue.py): Implemented.
- T080 (packages/schemas/github/issue.py): Implemented.
- T081 (tests/packages/schemas/github/test_pull_request.py): Implemented.
- T082 (packages/schemas/github/pull_request.py): Implemented.
- T083 (tests/packages/schemas/github/test_commit.py): Implemented.
- T084 (packages/schemas/github/commit.py): Implemented.
- T085 (tests/packages/schemas/github/test_branch.py): Implemented.

## Batch 10 (Tasks 91-100)
- T086 (packages/schemas/github/branch.py): Implemented.
- T087 (tests/packages/schemas/github/test_tag.py): Implemented.
- T088 (packages/schemas/github/tag.py): Implemented.
- T089 (tests/packages/schemas/github/test_github_label.py): Implemented.
- T090 (packages/schemas/github/github_label.py): Implemented.
- T091 (tests/packages/schemas/github/test_milestone.py): Implemented.
- T092 (packages/schemas/github/milestone.py): Implemented.
- T093 (tests/packages/schemas/github/test_comment.py): Implemented.
- T094 (packages/schemas/github/comment.py): Implemented.
- T095 (tests/packages/schemas/github/test_release.py): Implemented.

## Batch 11 (Tasks 101-110)
- T096 (packages/schemas/github/release.py): Implemented.
- T097 (tests/packages/schemas/github/test_documentation.py): Implemented.
- T098 (packages/schemas/github/documentation.py): Implemented.
- T099 (tests/packages/schemas/github/test_binary_asset.py): Implemented.
- T100 (packages/schemas/github/binary_asset.py): Implemented.
- T101 (tests/packages/schemas/gmail/test_email.py): Implemented.
- T102 (packages/schemas/gmail/email.py): Implemented.
- T103 (tests/packages/schemas/gmail/test_thread.py): Implemented.
- T104 (packages/schemas/gmail/thread.py): Implemented.
- T105 (tests/packages/schemas/gmail/test_gmail_label.py): Implemented.

## Batch 12 (Tasks 111-120)
- T106 (packages/schemas/gmail/gmail_label.py): Implemented.
- T107 (tests/packages/schemas/gmail/test_attachment.py): Implemented.
- T108 (packages/schemas/gmail/attachment.py): Implemented.
- T109 (tests/packages/schemas/reddit/test_subreddit.py): Implemented.
- T110 (packages/schemas/reddit/subreddit.py): Implemented.
- T111 (tests/packages/schemas/reddit/test_reddit_post.py): Implemented.
- T112 (packages/schemas/reddit/reddit_post.py): Implemented.
- T113 (tests/packages/schemas/reddit/test_reddit_comment.py): Implemented.
- T114 (packages/schemas/reddit/reddit_comment.py): Implemented.
- T115 (tests/packages/schemas/youtube/test_video.py): Implemented.

## Batch 13 (Tasks 121-130)
- T116 (packages/schemas/youtube/video.py): Implemented.
- T117 (tests/packages/schemas/youtube/test_channel.py): Implemented.
- T118 (packages/schemas/youtube/channel.py): Implemented.
- T119 (tests/packages/schemas/youtube/test_transcript.py): Implemented.
- T120 (packages/schemas/youtube/transcript.py): Implemented.
- T121 (tests/packages/schemas/tailscale/test_tailscale_device.py): Implemented.
- T122 (packages/schemas/tailscale/tailscale_device.py): Implemented.
- T123 (tests/packages/schemas/tailscale/test_tailscale_network.py): Implemented.
- T124 (packages/schemas/tailscale/tailscale_network.py): Implemented.
- T125 (tests/packages/schemas/tailscale/test_tailscale_acl.py): Implemented.

## Batch 14 (Tasks 131-140)
- T126 (packages/schemas/tailscale/tailscale_acl.py): Implemented.
- T127 (tests/packages/schemas/unifi/test_unifi_device.py): Implemented.
- T128 (packages/schemas/unifi/unifi_device.py): Implemented.
- T129 (tests/packages/schemas/unifi/test_unifi_client.py): Implemented.
- T130 (packages/schemas/unifi/unifi_client.py): Implemented.
- T131 (tests/packages/schemas/unifi/test_unifi_network.py): Implemented.
- T132 (packages/schemas/unifi/unifi_network.py): Implemented.
- T133 (tests/packages/schemas/unifi/test_unifi_site.py): Implemented.
- T134 (packages/schemas/unifi/unifi_site.py): Implemented.
- T135 (tests/packages/schemas/unifi/test_port_forwarding_rule.py): Implemented.

## Batch 15 (Tasks 141-150)
- T136 (packages/schemas/unifi/port_forwarding_rule.py): Implemented.
- T137 (tests/packages/schemas/unifi/test_firewall_rule.py): Implemented.
- T138 (packages/schemas/unifi/firewall_rule.py): Implemented.
- T139 (tests/packages/schemas/unifi/test_traffic_rule.py): Implemented.
- T140 (packages/schemas/unifi/traffic_rule.py): Implemented.
- T141 (tests/packages/schemas/unifi/test_traffic_route.py): Implemented.
- T142 (packages/schemas/unifi/traffic_route.py): Implemented.
- T143 (tests/packages/schemas/unifi/test_nat_rule.py): Implemented.
- T144 (packages/schemas/unifi/nat_rule.py): Implemented.
- T145 (tests/packages/schemas/web/test_document.py): Implemented.

## Batch 16 (Tasks 151-160)
- T146 (packages/schemas/web/document.py): Implemented.
- T147 (tests/packages/graph/writers/test_person_writer.py): Implemented.
- T148 (packages/graph/writers/person_writer.py): Implemented.
- T149 (packages/graph/writers/person_writer.py): Implemented.
- T150 (tests/packages/graph/writers/test_organization_writer.py): Implemented.
- T151 (packages/graph/writers/organization_writer.py): Implemented.
- T152 (packages/graph/writers/organization_writer.py): Implemented.
- T153 (tests/packages/graph/writers/test_place_writer.py): Implemented.
- T154 (packages/graph/writers/place_writer.py): Implemented.
- T155 (packages/graph/writers/place_writer.py): Implemented.

## Batch 17 (Tasks 161-170)
- T156 (tests/packages/graph/writers/test_event_writer.py): Implemented.
- T157 (packages/graph/writers/event_writer.py): Implemented.
- T158 (packages/graph/writers/event_writer.py): Implemented.
- T159 (tests/packages/graph/writers/test_file_writer.py): Implemented.
- T160 (packages/graph/writers/file_writer.py): Implemented.
- T161 (packages/graph/writers/file_writer.py): Implemented.
- T162 (tests/packages/graph/writers/test_docker_compose_writer.py): Implemented.
- T163 (packages/graph/writers/docker_compose_writer.py): Implemented.
- T164 (packages/graph/writers/docker_compose_writer.py): Implemented.
- T165 (tests/packages/graph/writers/test_swag_writer.py): Implemented.

## Batch 18 (Tasks 171-180)
- T166 (packages/graph/writers/swag_writer.py): Implemented.
- T167 (packages/graph/writers/swag_writer.py): Implemented.
- T168 (tests/packages/graph/writers/test_github_writer.py): Implemented.
- T169 (packages/graph/writers/github_writer.py): Implemented.
- T170 (packages/graph/writers/github_writer.py): Implemented.
- T171 (tests/packages/graph/writers/test_gmail_writer.py): Implemented.
- T172 (packages/graph/writers/gmail_writer.py): Implemented.
- T173 (packages/graph/writers/gmail_writer.py): Implemented.
- T174 (tests/packages/graph/writers/test_reddit_writer.py): Implemented.
- T175 (packages/graph/writers/reddit_writer.py): Implemented.

## Batch 19 (Tasks 181-190)
- T176 (packages/graph/writers/reddit_writer.py): Implemented.
- T177 (tests/packages/graph/writers/test_youtube_writer.py): Implemented.
- T178 (packages/graph/writers/youtube_writer.py): Implemented.
- T179 (packages/graph/writers/youtube_writer.py): Implemented.
- T180 (tests/packages/graph/writers/test_tailscale_writer.py): Implemented.
- T181 (packages/graph/writers/tailscale_writer.py): Implemented.
- T182 (packages/graph/writers/tailscale_writer.py): Implemented.
- T183 (tests/packages/graph/writers/test_unifi_writer.py): Implemented.
- T184 (packages/graph/writers/unifi_writer.py): Implemented.
- T185 (packages/graph/writers/unifi_writer.py): Implemented.

## Batch 20 (Tasks 191-200)
- T186 (tests/packages/graph/writers/test_document_writer.py): Implemented.
- T187 (packages/graph/writers/document_writer.py): Implemented.
- T188 (packages/graph/writers/document_writer.py): Implemented.
- T189 (tests/packages/graph/writers/test_relationship_writer.py): Implemented.
- T190 (packages/graph/writers/relationship_writer.py): Implemented.
- T191 (packages/graph/writers/relationship_writer.py): Implemented.
- T192 (tests/packages/ingest/readers/test_docker_compose.py): Implemented.
- T193 (packages/ingest/readers/docker_compose.py): Implemented.
- T194 (packages/ingest/readers/docker_compose.py): Implemented.
- T195 (tests/packages/ingest/readers/test_swag.py): Implemented.
