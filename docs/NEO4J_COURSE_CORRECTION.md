# SWAG Reader (2 models - already exist):
Proxy ✅ (exists)
  - What exactly is Proxy? What does it represent?
Service ✅ (exists, but will be deleted and recreated)

From the SWAG configs, I want to extract:
    - server_name - the subdomain
    - upstream_app - container name/hostname/IP for the service
    - upstream_port - the port the service is running on
    - upstream_proto - http / https
    - location - all location blocks exposed, and their upstream_app/port/proto/auth
    - auth - is authelia enabled for the service? if so, which location blocks? We check by looking to see if include /config/nginx/authelia-location.conf is uncommented in the location blocks
    - Headers? Should we extract any headers being set in the config? Probably right?

# Docker Compose Reader (5 models):
ComposeProject
ComposeService
ComposeNetwork
ComposeVolume
PortBinding

In addition to ComposeProject, ComposeService, ComposeNetwork, ComposeVolume, and PortBinding models, I want to extract:
    - Environment Variables: Key-value pairs defined under the environment section of each service.
    - Dependencies: Information about service dependencies defined using the depends_on attribute.
    - Image Details: The Docker image used for each service, including tags.
    - Health Checks: Any health check configurations defined for the services.
    - Build Context: Information about the build context and Dockerfile location if the service is built from a Dockerfile.
    - Devices: Any device mappings defined for the services.

We will also need to create a ComposeFile model to represent the entire Docker Compose file itself. This model will serve as the root entity that ties together all the other components. 

# GitHub Reader (9 models):
Repository
Issue
PullRequest
Commit
Branch
Tag
Label
Milestone
Comment
   - What is Tag, Label, and Milestone? Do you think those are necessary/useful?
   - What is comment? What exactly would that represent?
   - What about Organization and User models? Or are those not necessary because that would be covered by our Core entities?
   - What about a model for Releases as well?
   - Would it be useful to have a model for the README file of the repository?

Github repos consist of only a few different types of files really - code files, documentation files (README.md, etc), configuration files (like docker-compose.yml, .env.example, .conf), and other assets (images, etc). We should probably ingest/extract each type of file differently based on its type, right? 

Like docker-compose.yaml would be handled by the Docker Compose Reader(we would need to make sure that in addition to the normal models the docker compose reader uses, we capture repo specific information as well).

Documentation (README.md) would be handled by a Documentation Reader.

Code files would be handled by a Code Reader. For code files, we would probably want to extract things like:
   - Programming language
   - Lines of code
   - Functions/Classes defined
   - Dependencies/Imports
   - Code complexity metrics
   - Test coverage (if applicable)
   - Code comments and documentation strings
   - Repository structure and file hierarchy
   - The last modified date and author of the code file
   - The repository the code file belongs to

We would mainly want to use something like treesitter to extract an AST representation of the code file and store that as well for advanced code analysis, right?

And for assets, like images, etc, we would probably just want to store them as binary files in our storage system and link them to the repo entity?

# Gmail Reader (4 models):
Email
Thread
Label (conflicts with GitHub Label - need namespacing)
Attachment

- What about Contacts? Should we have a model for Contacts as well? Or once again, is that covered by our Core entities?

# Tailscale Reader (3 models):
TailscaleDevice
TailscaleNetwork
TailscaleACL
- What is TailscaleACL? What exactly would that represent?

We also want to extract:
    - Device OS: The operating system running on the Tailscale device.
    - Tailscale IPv4 and IPv6 addresses: The IP addresses assigned to the device by Tailscale.
    - OS hostname
    - Short domain
    - Full domain
    - Endpoints: The network endpoints associated with the device.
    - Key Expiry: The expiration date of the device's Tailscale key.
    - Exit Node status: Whether a device is configured as an exit node.
    - Subnet routes: Any subnet routes advertised by the device.
    - SSH access: Whether Tailscale SSH access is enabled for the device.
    - Tailnet DNS name
    - Global nameservers
    - Search Domains

# Unifi Reader (4 models):
UnifiDevice
UnifiClient
UnifiNetwork
UnifiSite

I also want to extract:
    - MAC Address for Devices and Clients
    - IP Address for Devices and Clients
    - Device Name for Devices and Clients
    - Link Speed for Devices and Clients
    - Connection Type for Devices and Clients (wired/wireless)
    - Uptime for Clients and Devices
    - Firmware Version for Devices
    - WAN IP Address for Sites
    - Gateway IP
    - DNS Servers
    - Wifi Name
    - Port forwarding rules
    - Firewall rules
    - NAT rules
    - QoS Rules
    - Static Routes

Now I'm not entirely sure if we're able to extract all of this information via the Unifi API, we are going to need to dispatch some research specialist agents to investigate, but if we can, we should.

# Reddit Reader (3 models):
Subreddit
RedditPost
RedditComment

# YouTube Reader (3 models):
Video
Channel
Transcript (or reuse core File)


# Notes
For all of the things I said we want to extract for each reader, we need to make sure that we are actually able to extract that information from the source. We may need to dispatch research specialist agents to investigate the source systems and determine what information is available and how to extract it. Also, let's make sure all of the things I said we want to extract aren't already being extracted by Core entities or existing models.

We will also need to create any new models and writers that are necessary to represent the data we are extracting.

Obviously we are going to need to make new models for each of these new entities we want to extract as well. We should follow the same conventions and patterns we have used for our existing models to ensure consistency and maintainability.

Also, for each reader, we need to make sure that we are properly handling relationships between entities. For example, in the GitHub Reader, we need to make sure that Issues are linked to their respective Repository, Pull Requests are linked to their respective Repository, Commits are linked to their respective Branch, etc. Properly modeling these relationships is crucial for effective data retrieval and analysis later on.

# Enrichment
In addition to just extracting and storing the raw data from each source, we should also consider implementing enrichment processes for each reader such as:

    - Docker Compose + SWAG + Tailscale + Unifi + ElasticSearch(Contains syslog from all of my devices): We can enrich the data by correlating information between these readers. For example, we can link services defined in Docker Compose files to their corresponding SWAG proxy configurations, Tailscale devices, and Unifi clients. This will provide a more comprehensive view of the infrastructure and how different components interact with each other. We should have very detailed relationships between these models to represent the full picture of the infrastructure. This is priority #1 for enrichment. This will help us understand how our services are exposed, secured, and accessed across the network, as well as provide insights into dependencies and potential points of failure.

    - GitHub: We can enrich repository data by linking it to related issues, pull requests, and commits. We can also analyze commit messages to extract keywords and topics, which can help in categorizing repositories and identifying trends. 

    - Github + Firecrawl: We can enrich GitHub repository data with documentation crawled from the web using Firecrawl. This can help provide additional context and information about the repositories, such as usage instructions, best practices, and related resources. We could link the README files and other documentation pages to their respective repositories in our graph.

    - Gmail + Google Calendar + Google Contacts: We can enrich email data by linking it to calendar events and contacts. For example, we can identify emails related to specific meetings or events and link them to the corresponding calendar entries. We can also link emails to contacts in the user's address book, which can help in identifying important correspondents and relationships.

    - YouTube + Reddit + Firecrawl: We can enrich YouTube video data by linking it to related Reddit posts and comments, as well as documentation crawled from the web using Firecrawl. This can help provide additional context and information about the videos, such as discussions, reviews, and related resources.

# Develop Using TDD (Test-Driven Development) Approach - RED-GREEN-REFACTOR

Finally, we need to make sure that we are properly testing each reader and its associated models to ensure that they are functioning correctly and efficiently. This includes unit tests for individual components as well as integration tests to ensure that the entire ingestion process works as expected.

Remember, we are developing using a TDD (Test-Driven Development) approach, so we should be writing tests before implementing the actual functionality. This will help us catch issues early and ensure that our code is robust and reliable. RED-GREEN-REFACTOR!

# Follow-Up Clarifications Part 2

# SWAG Reader Clarifications
What is Proxy?
Proxy node = The SWAG reverse proxy itself (the nginx container)
Currently just a single node with name="swag" that acts as the central routing hub
Think of it as: (:Proxy {name: "swag"})-[:ROUTES_TO {host, path, tls}]->(:Service {name: "api"})
Your extraction requirements are ALL extractable from nginx config:
✅ server_name - already extracted
✅ upstream_app/port/proto - currently extracts as service name, can parse URL fully
    - No don't parse the URL proxy_pass URL, it would just be variables:
        Exmaple:
        ```
        set $upstream_app 100.74.16.82;
        set $upstream_port 4210;
        set $upstream_proto http;
        proxy_pass $upstream_proto://$upstream_app:$upstream_port;
        ```
    - Just extract the three variables as-is

✅ location blocks - already extracted
✅ auth (authelia) - NOT currently extracted, need to add check for include /config/nginx/authelia-location.conf
    - Definitiely add this, very useful for security analysis
✅ Headers - NOT currently extracted, need to parse add_header, proxy_set_header directives
    - Yes, extract headers being set in the config - useful for security and debugging

# Docker Compose Additions
All your requirements are extractable from docker-compose.yml: Already in YAML:
✅ Environment Variables (under environment:)
✅ Dependencies (depends_on:)
✅ Image Details (image: with tags)
✅ Health Checks (healthcheck:)
✅ Build Context (build: with context: and dockerfile:)
✅ Devices (devices:)

ComposeFile as root entity - Excellent idea. 
    - Should we do this for our SWAG Reader as well?

Structure:
ComposeFile
  ├── ComposeProject (metadata)
  ├── ComposeService[] (list)
  ├── ComposeNetwork[] (list)
  └── ComposeVolume[] (list)

# GitHub Reader Deep Dive
Answering your questions:
Tag vs Label vs Milestone:
Tag: Git tags (v1.0.0, release markers) - USEFUL for version tracking
Label: Issue/PR labels (bug, feature, priority) - USEFUL for categorization
Milestone: Project milestones (v2.0, Q1 2025) - USEFUL for roadmap tracking
Verdict: Keep all three
Comment:
Comments on Issues/PRs
USEFUL for discussion threads, technical decisions, Q&A context
Organization/User:
Should map to Core Person/Organization entities
GitHub User → Person (with github_username property)
GitHub Org → Organization (with github_org property)
Releases:
YES, add Release model - distinct from Tags
Has release notes, assets (binaries), publication date
README model:
Should be File (core entity) with file_type: "documentation"
Or create Documentation reader-specific type
Your file type strategy is EXACTLY right:
GitHub Repository Files:
├── Code files (.py, .ts, .rs) → CodeFile entity + AST extraction (treesitter)
├── Documentation (README.md, docs/*.md) → Documentation entity
├── Config files (docker-compose.yml, .env) → Respective readers
└── Assets (images, binaries) → BinaryAsset entity (reference only)
For code files with treesitter:
Extract: language, LOC, functions/classes, imports, complexity
Store AST as JSONB in PostgreSQL or as graph nodes
This is a MAJOR feature - might be Phase 2?
Question: Is code AST extraction in scope for THIS refactor, or future work?
    - AST extraction will be future work (Phase 2). 


# Gmail Reader
Contacts:
Should map to Core Person entity
Gmail Contact → Person (with email, name, phone properties)
Link: (:Email)-[:FROM]->(:Person)

# Tailscale Reader
TailscaleACL:
Access Control Lists - rules defining which devices can access which devices
Example: {"action": "accept", "src": ["tag:dev"], "dst": ["tag:prod:*"]}
USEFUL for security analysis
All your additional fields are extractable from Tailscale API:
✅ Device OS (os)
✅ IPv4/IPv6 (addresses)
✅ Hostnames (hostname, name)
✅ Endpoints (endpoints)
✅ Key expiry (keyExpiryDisabled, expires)
✅ Exit node (isExitNode)
✅ Subnet routes (advertisedRoutes, enabledRoutes)
✅ SSH (enableSSH)
✅ DNS names, nameservers (tailnetDNS, dns)

# Unifi Reader
Need research agents to verify API capabilities. Most of your requirements are in Unifi API:
✅ MAC/IP/Name/Link Speed/Connection Type/Uptime (device/client stats)
✅ Firmware Version (device info)
✅ WAN IP/Gateway/DNS (site config)
✅ Wifi Name (WLAN config)
⚠️ Port forwarding/Firewall/NAT/QoS rules - Need research agent to verify
⚠️ Static routes - Need research agent to verify

# Enrichment Strategy
Your enrichment priorities are perfect: Priority 1: Infrastructure Correlation (Docker + SWAG + Tailscale + Unifi + Elasticsearch)
Example: (:ComposeService {name: "api"})-[:PROXIED_BY]->(:ProxyRoute {host: "api.domain.com"})
Example: (:TailscaleDevice {hostname: "server"})-[:RUNS]->(:ComposeService {name: "api"})
Example: (:UnifiClient {ip: "192.168.1.100"})-[:CONNECTS_TO]->(:TailscaleDevice)
This creates a complete infrastructure topology graph.

# Scope Clarification 

Core + Extended Extraction

All your additional fields (SWAG auth, Docker env vars, Tailscale ACLs, Unifi network rules)
Research agents to verify API capabilities
NO code AST extraction
NO enrichment yet

