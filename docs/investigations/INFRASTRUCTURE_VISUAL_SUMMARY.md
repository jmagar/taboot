# Infrastructure Visual Summary

## Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    TABOOT DOCKER NETWORK (bridge)               │
│                          taboot-net                              │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  API & WEB TIER                          │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ taboot-api  │  │ taboot-web   │  │ taboot-web   │  │  │
│  │  │ (FastAPI)   │  │ (Next.js)    │  │ (Next.js)    │  │  │
│  │  │ :8000       │  │ :3000        │  │ :3000 (2nd)  │  │  │
│  │  │ 2GB RAM     │  │ 1GB RAM      │  │ 1GB RAM      │  │  │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  │         │                │                 │           │  │
│  └─────────┼────────────────┼─────────────────┼───────────┘  │
│            │                │                 │                │
│  ┌─────────┼────────────────┼─────────────────┼───────────┐  │
│  │         │   DATA TIER    │                 │           │  │
│  │  ┌──────▼──────┐  ┌──────▼────────┐  ┌────▼─────┐  │  │
│  │  │ taboot-db   │  │ taboot-cache  │  │taboot-   │  │  │
│  │  │(PostgreSQL) │  │   (Redis)     │  │graph     │  │  │
│  │  │ :5432 ⚠️    │  │ :6379 ⚠️      │  │(Neo4j)   │  │  │
│  │  │ 4GB RAM ✓   │  │ 2GB RAM ✓     │  │:7474 ⚠️  │  │  │
│  │  └─────────────┘  └───────────────┘  │ 6GB ✓    │  │  │
│  │                                        └──────────┘  │  │
│  └────────────────────────────────────────────────────┬───┘  │
│                                                        │      │
│  ┌────────────────────────────────────────────────────▼───┐  │
│  │              GPU SERVICES TIER                         │  │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────┐ │  │
│  │  │ taboot-vectors  │  │ taboot-embed │  │taboot-   │ │  │
│  │  │   (Qdrant)      │  │   (TEI)      │  │rerank    │ │  │
│  │  │ :7000/4204 ⚠️   │  │ :8080 ✓      │  │:8081 ✓   │ │  │
│  │  │ 8GB ⚠️          │  │ 6GB ⚠️       │  │4GB ⚠️    │ │  │
│  │  └────────┬────────┘  └──────┬───────┘  └────┬─────┘ │  │
│  │           │                  │                │       │  │
│  │  ┌────────▼────────────────────────────────────▼───┐  │  │
│  │  │         taboot-ollama (Qwen3-4B)               │  │  │
│  │  │ GPU Inference, :11434 ⚠️                       │  │  │
│  │  │ 8GB Memory ⚠️                                  │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         PIPELINE & SUPPORT TIER                       │  │
│  │  ┌───────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │ taboot-worker │  │ taboot-      │  │taboot-  │  │  │
│  │  │ (Extraction)  │  │ crawler      │  │playwright   │  │
│  │  │ 4GB ⚠️        │  │(Firecrawl)   │  │(Browser)│  │  │
│  │  │               │  │ 2GB ⚠️       │  │1GB ⚠️   │  │  │
│  │  └───────────────┘  └──────────────┘  └──────────┘  │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│ LEGEND: ✓ = Has limits  ⚠️ = Missing limits  🔴 = Exposed ports
│ ⚠️ = Port exposed to 0.0.0.0 (insecure)                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Resource Allocation Current vs. Recommended

### Memory Allocation (32GB System)

```
CURRENT STATE (DANGEROUS):
┌─────────────────────────────────────────────────────────┐
│                    32GB System RAM                       │
│  ┌─────────────────────────────────────────────────────┐│
│  │   NO LIMITS - Any service can consume all RAM!      ││
│  │   Risk: Single runaway process → OOM kills all     ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘

RECOMMENDED STATE (PROTECTED):
┌─────────────────────────────────────────────────────────┐
│                    32GB System RAM                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Vectors   │ │Embed     │ │Rerank    │ │Ollama    │  │
│  │ 8GB max  │ │ 6GB max  │ │ 4GB max  │ │ 8GB max  │  │
│  │(shared)  │ │(shared)  │ │(shared)  │ │(shared)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │PostgreSQL│ │Redis     │ │Neo4j     │              │
│  │ 4GB max  │ │ 2GB max  │ │ 6GB max  │              │
│  └──────────┘ └──────────┘ └──────────┘              │
│                                                       │
│  TOTAL: 26GB allocated, 6GB reserved for OS/kernel  │
└─────────────────────────────────────────────────────┘
```

### GPU VRAM Allocation (RTX 4070 = 24GB)

```
CURRENT (BROKEN):
┌────────────────────────────────────────────┐
│        RTX 4070 (24GB VRAM)                │
│  ┌──────────────────────────────────────┐ │
│  │ ✅ taboot-vectors (locked GPU)       │ │
│  │ ⏳ taboot-embed (waiting...)         │ │
│  │ ⏳ taboot-rerank (waiting...)        │ │
│  │ ⏳ taboot-ollama (waiting...)        │ │
│  │                                       │ │
│  │ ONLY 1 SERVICE CAN RUN AT A TIME!   │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘

RECOMMENDED (SHARED):
┌────────────────────────────────────────────┐
│        RTX 4070 (24GB VRAM) - Shared       │
│  ┌──────────────────────────────────────┐ │
│  │ ✅ taboot-vectors (8GB allocated)    │ │
│  │ ✅ taboot-embed (6GB allocated)      │ │
│  │ ✅ taboot-rerank (4GB allocated)     │ │
│  │ ✅ taboot-ollama (4GB allocated)     │ │
│  │                                       │ │
│  │ All 4 services can run simultaneously!
│  │ Total: 22GB allocated, 2GB headroom  │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

---

## Port Exposure Risk Map

```
╔═══════════════════════════════════════════════════════════╗
║              NETWORK EXPOSURE ANALYSIS                    ║
╠═══════════════════════════════════════════════════════════╣
║ Service        Port  Exposure    Risk Level   Fix         ║
╠═══════════════════════════════════════════════════════════╣
║ PostgreSQL     4201  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║ Redis          4202  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║ Neo4j          4205  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║ Neo4j Bolt     4206  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║ Qdrant HTTP    4203  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║ Qdrant gRPC    4204  0.0.0.0 ⚠️  🔴 CRITICAL  127.0.0.1  ║
║                                                            ║
║ FastAPI        4209  0.0.0.0 ✓  🟡 OK        Keep Open   ║
║ Next.js Web    4211  0.0.0.0 ✓  🟡 OK        Keep Open   ║
║ Firecrawl      4200  0.0.0.0 ✓  🟡 OK        Keep Open   ║
║ Ollama        4214  0.0.0.0 ⚠️  🟠 MEDIUM    127.0.0.1   ║
║ TEI           4207   0.0.0.0 ✓  🟢 LOW       Optional    ║
║ Reranker      4208   0.0.0.0 ✓  🟢 LOW       Optional    ║
║ Playwright    4211   0.0.0.0 ✓  🟢 LOW       Optional    ║
╚═══════════════════════════════════════════════════════════╝

🔴 CRITICAL: Unauthenticated database access from network
🟠 MEDIUM:   Exposes inference services
🟡 OK:       API and Web tier (expected)
🟢 LOW:      Support services
```

---

## Health Check Status Dashboard

```
╔════════════════════════════════════════════════════════════════╗
║                  HEALTH CHECK CONFIGURATION                    ║
╠════════════════════════════════════════════════════════════════╣
║ Service          Method      Interval  Timeout  Start   Ready  ║
╠════════════════════════════════════════════════════════════════╣
║ taboot-vectors   TCP+bash    30s       10s      40s     ✅    ║
║ taboot-embed     HTTP GET    30s       10s      20s     ✅    ║
║ taboot-rerank    HTTP GET    30s       10s      20s     ✅    ║
║ taboot-graph     Cypher      30s       10s      40s     ✅    ║
║ taboot-cache     PING        30s       10s      10s     ✅    ║
║ taboot-ollama    HTTP GET    30s       10s      60s     ✅    ║
║ taboot-crawler   HTTP GET    30s       10s      30s     ✅    ║
║ taboot-db        pg_isready  5s        5s       15s     ✅    ║
║ taboot-api       HTTP GET    30s       10s      40s     ✅    ║
║ taboot-web       HTTP GET    30s       10s      40s     ✅    ║
║ taboot-worker    pgrep       30s       10s      30s     ⚠️    ║
║ taboot-playwright HTTP GET   30s       10s      20s     ✅    ║
║                                                                ║
║ LEGEND: ✅ = Good  ⚠️ = Fragile (pgrep-based)                ║
║                                                                ║
║ STARTUP SEQUENCE:                                             ║
║  1. PostgreSQL, Redis, Neo4j (10-15s)                         ║
║  2. Qdrant, TEI, Reranker (20-40s)                           ║
║  3. API, Ollama, Crawler (40-60s)                            ║
║  4. Web (60-80s)                                              ║
║  5. Worker (80-100s)                                          ║
║  TOTAL TIME TO READY: ~2-3 minutes                            ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Startup Dependency Graph

```
                         ┌─────────────────┐
                         │ docker-compose  │
                         │      up         │
                         └────────┬────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
            PostgreSQL        Redis            Neo4j
            (10-15s)        (10-15s)          (15-40s)
                │                 │                 │
                └─────────────────┼─────────────────┘
                                  │
                        ┌─────────┴──────────┐
                        │                    │
                        ▼                    ▼
                    Qdrant              Firecrawl
                   (15-30s)            (20-30s)
                        │                    │
                        ▼                    │
                    TEI Embed                │
                   (20-40s)                  │
                        │                    │
                ┌───────┴────────┐           │
                │                │           │
                ▼                ▼           │
            Reranker         Ollama          │
           (15-20s)         (30-60s)         │
                │                │           │
                └────────┬───────┴───────────┘
                         │
                         ▼
                    FastAPI
                   (40-50s)
                         │
                         ▼
                    Next.js Web
                   (40-50s)
                         │
                         ▼
                     Worker
                   (30-40s)

  Healthy:   ✅   Waiting:   ⏳   Failed:   ❌
```

---

## Volume Persistence Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                   PERSISTENT VOLUMES                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CRITICAL DATA (BACKUP REQUIRED)                           │
│  ┌────────────────────────────────────────────────────────┐│
│  │ taboot-db ──────────► PostgreSQL (Users, Sessions)     ││
│  │    ↓                   Backup: Daily, Retention: 30d  ││
│  │    └──► Soft-delete audit trail                       ││
│  │                                                         ││
│  │ taboot-graph_data ──► Neo4j (Knowledge Graph)          ││
│  │    ↓                   Backup: Daily, Retention: 7d   ││
│  │    └──► Regenerable via re-ingestion                  ││
│  │                                                         ││
│  │ taboot-vectors ──────► Qdrant (Vector Embeddings)      ││
│  │    ↓                   Backup: Daily, Retention: 3d   ││
│  │    └──► Regenerable via extraction pipeline           ││
│  └────────────────────────────────────────────────────────┘│
│                                                              │
│  EPHEMERAL CACHE (NO BACKUP NEEDED)                        │
│  ┌────────────────────────────────────────────────────────┐│
│  │ taboot-embed ────────► HF Model Cache                  ││
│  │    └──► Auto-downloads from HuggingFace               ││
│  │                                                         ││
│  │ taboot-rerank ───────► Transformer Cache               ││
│  │    └──► Auto-downloads from HuggingFace               ││
│  │                                                         ││
│  │ taboot-ollama ───────► LLM Model Cache                 ││
│  │    └──► Auto-downloads from Ollama registry           ││
│  │                                                         ││
│  │ spacy-models ────────► NLP Model Cache                 ││
│  │    └──► Auto-downloads from spaCy                     ││
│  │                                                         ││
│  │ taboot-cache ────────► Redis (Session/DLQ)            ││
│  │    └──► Recoverable via regeneration                  ││
│  └────────────────────────────────────────────────────────┘│
│                                                              │
│  TOTAL PERSISTENT STORAGE:                                 │
│  • PostgreSQL:      ~500MB-1GB (varies with users)        │
│  • Neo4j:           ~2-5GB (knowledge graph size)          │
│  • Qdrant:          ~5-10GB (vector index size)            │
│  • Cache volumes:   ~50GB (model files)                    │
│  ────────────────────────────────────────────────────────  │
│  TOTAL:             ~60-70GB typical usage                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Posture Summary

```
╔═════════════════════════════════════════════════════════════╗
║              SECURITY POSTURE SCORECARD                     ║
╠═════════════════════════════════════════════════════════════╣
║                                                             ║
║  NETWORK SECURITY                  Score: 4/10  ❌ RED     ║
║  ├─ Port exposure (0.0.0.0)         1/5   🔴              ║
║  ├─ Service isolation               2/5   🟠              ║
║  ├─ Egress filtering                0/5   🔴              ║
║  └─ TLS/mTLS                        1/5   🔴              ║
║                                                             ║
║  CONTAINER SECURITY                Score: 7/10  🟡 YELLOW ║
║  ├─ Non-root users                  5/5   ✅              ║
║  ├─ Read-only root filesystem       0/5   🔴              ║
║  ├─ Resource limits                 1/5   🔴              ║
║  └─ Security scanning               1/5   🔴              ║
║                                                             ║
║  DATA SECURITY                      Score: 5/10  🟠 ORANGE ║
║  ├─ Encryption at rest              0/5   🔴              ║
║  ├─ Backup strategy                 3/5   🟡              ║
║  ├─ Access controls                 1/5   🔴              ║
║  └─ Audit logging                   1/5   🔴              ║
║                                                             ║
║  OPERATIONAL SECURITY               Score: 8/10  🟡 YELLOW ║
║  ├─ Health monitoring                5/5   ✅              ║
║  ├─ Logging                         2/5   🟠              ║
║  ├─ Vulnerability scanning           0/5   🔴              ║
║  └─ Update policy                   1/5   🔴              ║
║                                                             ║
║  OVERALL SCORE: 6/10 🟠 NEEDS IMPROVEMENT                  ║
║                                                             ║
║  IMMEDIATE ACTIONS (This Week):                            ║
║  1. Fix database port exposure (Score +1)                  ║
║  2. Add memory limits (Score +1)                           ║
║  3. Fix GPU contention (Score +0.5)                        ║
║                                                             ║
║  → Target Score: 8/10 after fixes                          ║
╚═════════════════════════════════════════════════════════════╝
```

---

## Implementation Priority Matrix

```
                      Impact
                      (High)
                        ↑
                        │
                        │    ✅ CRITICAL
                        │   ┌──────────────────────────┐
                        │   │ Database Port Exposure   │
                        │   │ Memory Limits ──┐        │
                        │   │ GPU Contention ├──────┐  │
          ┌─────────────┼───┤                │      │  │
          │ Medium      │   │ Add CPU Limits ┌──────┘  │
          │ Impact      │   │ Backup Strategy          │
          │             │   │ Network Isolation        │
          │             │   └──────────────────────────┘
          │             │
          │             └─────────────────────────────→ Effort
          │            Quick              Complex
          │
        Effort: 2-4h    4-8h             8-16h+
        Timeline: Week 1 Week 1-2        Month 1+

Quick Wins (High Impact, Low Effort):
  • Database port exposure (2h)
  • Add memory limits (2h)
  • GPU device pinning (1h)

Strategic Investments (Medium Impact, High Effort):
  • Monitoring stack (16h)
  • Network segmentation (12h)
  • Encryption at rest (12h)

Nice-to-Have (Low Impact):
  • Image signing
  • RBAC policies
  • Advanced auditing
```

---

## Daily Operations Checklist

```
╔═══════════════════════════════════════════════════════════╗
║         DAILY OPERATIONS MONITORING (5 minutes)          ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  STARTUP CHECK:                                          ║
║  ☐ docker-compose ps (all green?)                       ║
║  ☐ docker stats (any service >90% memory?)              ║
║  ☐ nvidia-smi (all 4 GPU services active?)              ║
║                                                           ║
║  HEALTH CHECK:                                           ║
║  ☐ curl http://localhost:4209/health (API)              ║
║  ☐ curl http://localhost:4211/api/health (Web)          ║
║  ☐ docker-compose logs --tail=50 (errors?)              ║
║                                                           ║
║  RESOURCE MONITORING:                                   ║
║  ☐ Disk usage: df -h | grep -E "100%|9[0-9]%"           ║
║  ☐ Memory pressure: free -h (OOM killer active?)        ║
║  ☐ GPU memory: nvidia-smi (fragmented?)                 ║
║                                                           ║
║  DATABASE HEALTH:                                       ║
║  ☐ psql -c "SELECT COUNT(*) FROM auth.user"             ║
║  ☐ redis-cli PING → should reply PONG                   ║
║  ☐ cypher-shell "MATCH (n) RETURN count(n)" (Neo4j)     ║
║                                                           ║
║  BACKUP STATUS:                                         ║
║  ☐ ls -lah /backup/taboot | head (recent?)              ║
║  ☐ Check last backup timestamp < 25 hours               ║
║                                                           ║
║  WEEKLY TASKS (Friday):                                 ║
║  ☐ Review docker logs for warnings                      ║
║  ☐ Test backup restoration on test system               ║
║  ☐ Check for container image updates                    ║
║  ☐ Verify GPU memory doesn't fragment                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Architecture Decision Record

| Decision | Status | Rationale | Tradeoff |
|----------|--------|-----------|----------|
| Single bridge network | ✅ Active | Simple for single-user system | No microsegmentation |
| Named volumes | ✅ Active | Better than bind mounts | Less host control |
| Non-root containers | ✅ Active | Security best practice | Slightly slower startup |
| Health checks on all | ✅ Active | Prevents cascade failures | Resource overhead (~1%) |
| GPU resource limits | ❌ Not Implemented | Single RTX 4070 | Services block each other |
| Memory limits | ❌ Not Implemented | Single-user trust model | OOM risk |
| Backup strategy | 📋 Planned | 90-day retention | Storage cost |
| Network segmentation | 🔮 Future | Not needed for single-user | Defense-in-depth gap |

---

**Last Updated:** 2025-10-27
**For:** Taboot Infrastructure Audit
**Status:** Complete - Ready for Remediation
