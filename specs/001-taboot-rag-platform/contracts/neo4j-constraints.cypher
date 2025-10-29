// Neo4j Constraints and Indexes for Taboot Graph Schema
// Execute these queries during initialization (taboot init command)
// All constraints ensure uniqueness and enable fast lookups for the new graph model

// === LEGACY CONSTRAINT CLEANUP ===

DROP CONSTRAINT class_unique IF EXISTS;
DROP CONSTRAINT function_unique IF EXISTS;
DROP CONSTRAINT module_name IF EXISTS;
DROP CONSTRAINT variable_unique IF EXISTS;
DROP CONSTRAINT directory_path IF EXISTS;
DROP CONSTRAINT file_path IF EXISTS;
DROP CONSTRAINT repository_path IF EXISTS;

// === CORE ENTITY CONSTRAINTS ===

CREATE CONSTRAINT person_email_unique
IF NOT EXISTS
FOR (p:Person)
REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT organization_name_unique
IF NOT EXISTS
FOR (o:Organization)
REQUIRE o.name IS UNIQUE;

CREATE CONSTRAINT place_name_unique
IF NOT EXISTS
FOR (pl:Place)
REQUIRE pl.name IS UNIQUE;

CREATE CONSTRAINT event_name_unique
IF NOT EXISTS
FOR (e:Event)
REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT file_id_unique
IF NOT EXISTS
FOR (f:File)
REQUIRE f.file_id IS UNIQUE;

// === DOCKER COMPOSE ENTITY CONSTRAINTS ===

CREATE CONSTRAINT compose_file_path_unique
IF NOT EXISTS
FOR (f:ComposeFile)
REQUIRE f.file_path IS UNIQUE;

CREATE CONSTRAINT compose_project_key_unique
IF NOT EXISTS
FOR (p:ComposeProject)
REQUIRE (p.file_path, p.name) IS UNIQUE;

CREATE CONSTRAINT compose_service_key_unique
IF NOT EXISTS
FOR (s:ComposeService)
REQUIRE (s.compose_file_path, s.name) IS UNIQUE;

CREATE CONSTRAINT compose_network_key_unique
IF NOT EXISTS
FOR (n:ComposeNetwork)
REQUIRE (n.compose_file_path, n.name) IS UNIQUE;

CREATE CONSTRAINT compose_volume_key_unique
IF NOT EXISTS
FOR (v:ComposeVolume)
REQUIRE (v.compose_file_path, v.name) IS UNIQUE;

CREATE CONSTRAINT port_binding_key_unique
IF NOT EXISTS
FOR (p:PortBinding)
REQUIRE (p.compose_file_path, p.service_name, p.host_ip, p.host_port, p.container_port, p.protocol) IS UNIQUE;

CREATE CONSTRAINT environment_variable_key_unique
IF NOT EXISTS
FOR (e:EnvironmentVariable)
REQUIRE (e.compose_file_path, e.service_name, e.key) IS UNIQUE;

CREATE CONSTRAINT service_dependency_key_unique
IF NOT EXISTS
FOR (d:ServiceDependency)
REQUIRE (d.compose_file_path, d.source_service, d.target_service, d.condition) IS UNIQUE;

CREATE CONSTRAINT image_details_key_unique
IF NOT EXISTS
FOR (i:ImageDetails)
REQUIRE (i.compose_file_path, i.service_name, i.image_name, i.tag, i.registry) IS UNIQUE;

CREATE CONSTRAINT health_check_key_unique
IF NOT EXISTS
FOR (h:HealthCheck)
REQUIRE (h.compose_file_path, h.service_name, h.test) IS UNIQUE;

CREATE CONSTRAINT build_context_key_unique
IF NOT EXISTS
FOR (b:BuildContext)
REQUIRE (b.compose_file_path, b.service_name, b.context_path, b.dockerfile) IS UNIQUE;

CREATE CONSTRAINT device_mapping_key_unique
IF NOT EXISTS
FOR (d:DeviceMapping)
REQUIRE (d.compose_file_path, d.service_name, d.host_device, d.container_device) IS UNIQUE;

// === SWAG ENTITY CONSTRAINTS ===

CREATE CONSTRAINT swag_config_file_path_unique
IF NOT EXISTS
FOR (c:SwagConfigFile)
REQUIRE c.file_path IS UNIQUE;

CREATE CONSTRAINT proxy_key_unique
IF NOT EXISTS
FOR (p:Proxy)
REQUIRE (p.config_path, p.name) IS UNIQUE;

CREATE CONSTRAINT proxy_route_key_unique
IF NOT EXISTS
FOR (r:ProxyRoute)
REQUIRE (r.server_name, r.upstream_app, r.upstream_port, r.upstream_proto) IS UNIQUE;

CREATE CONSTRAINT location_block_path_unique
IF NOT EXISTS
FOR (l:LocationBlock)
REQUIRE (l.path, l.proxy_pass_url) IS UNIQUE;

CREATE CONSTRAINT upstream_config_key_unique
IF NOT EXISTS
FOR (u:UpstreamConfig)
REQUIRE (u.app, u.port, u.proto) IS UNIQUE;

CREATE CONSTRAINT proxy_header_key_unique
IF NOT EXISTS
FOR (h:ProxyHeader)
REQUIRE (h.header_type, h.header_name, h.header_value) IS UNIQUE;

// === GITHUB ENTITY CONSTRAINTS ===

CREATE CONSTRAINT repository_full_name_unique
IF NOT EXISTS
FOR (r:Repository)
REQUIRE r.full_name IS UNIQUE;

CREATE CONSTRAINT issue_repo_number_unique
IF NOT EXISTS
FOR (i:Issue)
REQUIRE (i.repo_full_name, i.number) IS UNIQUE;

CREATE CONSTRAINT pull_request_repo_number_unique
IF NOT EXISTS
FOR (p:PullRequest)
REQUIRE (p.repo_full_name, p.number) IS UNIQUE;

CREATE CONSTRAINT commit_sha_unique
IF NOT EXISTS
FOR (c:Commit)
REQUIRE c.sha IS UNIQUE;

CREATE CONSTRAINT branch_repo_name_unique
IF NOT EXISTS
FOR (b:Branch)
REQUIRE (b.repo_full_name, b.name) IS UNIQUE;

CREATE CONSTRAINT tag_repo_name_unique
IF NOT EXISTS
FOR (t:Tag)
REQUIRE (t.repo_full_name, t.name) IS UNIQUE;

CREATE CONSTRAINT github_label_repo_name_unique
IF NOT EXISTS
FOR (l:GitHubLabel)
REQUIRE (l.repo_full_name, l.name) IS UNIQUE;

CREATE CONSTRAINT milestone_repo_number_unique
IF NOT EXISTS
FOR (m:Milestone)
REQUIRE (m.repo_full_name, m.number) IS UNIQUE;

CREATE CONSTRAINT github_comment_id_unique
IF NOT EXISTS
FOR (c:Comment)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT release_repo_tag_unique
IF NOT EXISTS
FOR (r:Release)
REQUIRE (r.repo_full_name, r.tag_name) IS UNIQUE;

CREATE CONSTRAINT documentation_repo_path_unique
IF NOT EXISTS
FOR (d:Documentation)
REQUIRE (d.repo_full_name, d.file_path) IS UNIQUE;

CREATE CONSTRAINT binary_asset_repo_release_file_unique
IF NOT EXISTS
FOR (b:BinaryAsset)
REQUIRE (b.repo_full_name, b.release_tag, b.file_path) IS UNIQUE;

// === GMAIL ENTITY CONSTRAINTS ===

CREATE CONSTRAINT email_message_id_unique
IF NOT EXISTS
FOR (e:Email)
REQUIRE e.message_id IS UNIQUE;

CREATE CONSTRAINT thread_id_unique
IF NOT EXISTS
FOR (t:Thread)
REQUIRE t.thread_id IS UNIQUE;

CREATE CONSTRAINT gmail_label_id_unique
IF NOT EXISTS
FOR (l:GmailLabel)
REQUIRE l.label_id IS UNIQUE;

CREATE CONSTRAINT attachment_id_unique
IF NOT EXISTS
FOR (a:Attachment)
REQUIRE a.attachment_id IS UNIQUE;

// === REDDIT ENTITY CONSTRAINTS ===

CREATE CONSTRAINT subreddit_name_unique
IF NOT EXISTS
FOR (s:Subreddit)
REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT reddit_post_id_unique
IF NOT EXISTS
FOR (p:RedditPost)
REQUIRE p.post_id IS UNIQUE;

CREATE CONSTRAINT reddit_comment_id_unique
IF NOT EXISTS
FOR (c:RedditComment)
REQUIRE c.comment_id IS UNIQUE;

// === YOUTUBE ENTITY CONSTRAINTS ===

CREATE CONSTRAINT youtube_video_id_unique
IF NOT EXISTS
FOR (v:Video)
REQUIRE v.video_id IS UNIQUE;

CREATE CONSTRAINT youtube_channel_id_unique
IF NOT EXISTS
FOR (c:Channel)
REQUIRE c.channel_id IS UNIQUE;

CREATE CONSTRAINT transcript_key_unique
IF NOT EXISTS
FOR (t:Transcript)
REQUIRE (t.video_id, t.language) IS UNIQUE;

// === TAILSCALE ENTITY CONSTRAINTS ===

CREATE CONSTRAINT tailscale_device_id_unique
IF NOT EXISTS
FOR (d:TailscaleDevice)
REQUIRE d.device_id IS UNIQUE;

CREATE CONSTRAINT tailscale_network_id_unique
IF NOT EXISTS
FOR (n:TailscaleNetwork)
REQUIRE n.network_id IS UNIQUE;

CREATE CONSTRAINT tailscale_acl_id_unique
IF NOT EXISTS
FOR (a:TailscaleACL)
REQUIRE a.rule_id IS UNIQUE;

// === UNIFI ENTITY CONSTRAINTS ===

CREATE CONSTRAINT unifi_device_mac_unique
IF NOT EXISTS
FOR (d:UnifiDevice)
REQUIRE d.mac IS UNIQUE;

CREATE CONSTRAINT unifi_client_mac_unique
IF NOT EXISTS
FOR (c:UnifiClient)
REQUIRE c.mac IS UNIQUE;

CREATE CONSTRAINT unifi_network_id_unique
IF NOT EXISTS
FOR (n:UnifiNetwork)
REQUIRE n.network_id IS UNIQUE;

CREATE CONSTRAINT unifi_site_id_unique
IF NOT EXISTS
FOR (s:UnifiSite)
REQUIRE s.site_id IS UNIQUE;

CREATE CONSTRAINT port_forwarding_rule_id_unique
IF NOT EXISTS
FOR (r:PortForwardingRule)
REQUIRE r.rule_id IS UNIQUE;

CREATE CONSTRAINT firewall_rule_id_unique
IF NOT EXISTS
FOR (r:FirewallRule)
REQUIRE r.rule_id IS UNIQUE;

CREATE CONSTRAINT traffic_rule_id_unique
IF NOT EXISTS
FOR (r:TrafficRule)
REQUIRE r.rule_id IS UNIQUE;

CREATE CONSTRAINT traffic_route_id_unique
IF NOT EXISTS
FOR (r:TrafficRoute)
REQUIRE r.route_id IS UNIQUE;

CREATE CONSTRAINT nat_rule_id_unique
IF NOT EXISTS
FOR (r:NATRule)
REQUIRE r.rule_id IS UNIQUE;

// === WEB ENTITY CONSTRAINTS ===

CREATE CONSTRAINT document_id_unique
IF NOT EXISTS
FOR (d:Document)
REQUIRE d.doc_id IS UNIQUE;

// === RELATIONSHIP PROPERTY INDEXES ===

CREATE INDEX depends_on_confidence_idx
IF NOT EXISTS
FOR ()-[r:DEPENDS_ON]-()
ON (r.confidence);

CREATE INDEX routes_to_host_idx
IF NOT EXISTS
FOR ()-[r:ROUTES_TO]-()
ON (r.host);

CREATE INDEX mentions_chunk_id_idx
IF NOT EXISTS
FOR ()-[r:MENTIONS]-()
ON (r.chunk_id);

CREATE INDEX mentions_doc_id_idx
IF NOT EXISTS
FOR ()-[r:MENTIONS]-()
ON (r.doc_id);

// === CORE PERFORMANCE INDEXES ===

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

// Verification helpers

SHOW CONSTRAINTS;
SHOW INDEXES;
