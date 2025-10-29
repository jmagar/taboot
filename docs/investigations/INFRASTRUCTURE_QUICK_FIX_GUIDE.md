# Infrastructure Quick Fix Guide
## Critical Issues & Copy-Paste Solutions

---

## 🔴 CRITICAL - Fix This First

### Issue #1: Database Port Exposure (30 minutes)

**Problem:** All databases exposed to network (0.0.0.0:PORT)

**Quick Fix:**
```yaml
# In docker-compose.yaml, change all database port bindings:

# BEFORE:
taboot-graph:
  ports:
    - "${NEO4J_HTTP_PORT:-4205}:7474"
    - "${NEO4J_BOLT_PORT:-4206}:7687"

# AFTER:
taboot-graph:
  ports:
    - "127.0.0.1:${NEO4J_HTTP_PORT:-4205}:7474"
    - "127.0.0.1:${NEO4J_BOLT_PORT:-4206}:7687"

# Repeat for:
# - taboot-vectors (Qdrant)
# - taboot-cache (Redis)
# - taboot-db (PostgreSQL)
```

**Verify:**
```bash
# Should fail to connect (good!)
nc -zv localhost 4201

# Should work locally
psql -h 127.0.0.1 -U taboot -d taboot
```

---

### Issue #2: Missing Memory Limits (1 hour)

**Problem:** Services have no memory limits → OOM crashes possible

**Quick Fix Template:**
```yaml
# Add this to EVERY service in docker-compose.yaml
deploy:
  resources:
    limits:
      memory: 2G          # Maximum allowed
    reservations:
      memory: 1G          # Guaranteed minimum
```

**Apply to these first (highest risk):**

```yaml
taboot-db:
  <<: *common-base
  # ... existing config ...
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 3G

taboot-vectors:
  <<: *common-base
  deploy:
    resources:
      limits:
        memory: 8G
      reservations:
        memory: 6G

taboot-embed:
  <<: *common-base
  deploy:
    resources:
      limits:
        memory: 6G
      reservations:
        memory: 5G

taboot-cache:
  <<: *common-base
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1.5G
```

**Verify:**
```bash
docker inspect taboot-db | grep -A5 '"Memory"'
# Should show: "Memory": 4294967296 (4G in bytes)
```

---

### Issue #3: GPU Resource Contention (1 hour)

**Problem:** 4 GPU services all claim "count: 1" → only 1 runs at a time

**Current Behavior:**
```
✅ taboot-vectors starts → locks GPU
⏳ taboot-embed waits indefinitely
⏳ taboot-rerank waits indefinitely
⏳ taboot-ollama waits indefinitely
```

**Quick Fix - Add GPU IDs:**
```yaml
x-gpu-deploy: &gpu-deploy
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ["0"]      # ADD THIS LINE
            capabilities: [gpu]
```

**Then Reduce Batch Sizes to Prevent OOM:**
```yaml
taboot-embed:
  environment:
    TEI_MAX_CONCURRENT_REQUESTS: "40"  # Reduce from 80

taboot-rerank:
  environment:
    RERANKER_BATCH_SIZE: "8"  # Reduce from 16
```

**Verify:**
```bash
# All 4 GPU services should be running
docker ps | grep taboot
nvidia-smi  # All services visible in GPU memory

# Check memory usage
docker stats --no-stream taboot-embed taboot-rerank
```

---

## ⚠️ HIGH PRIORITY - Fix This Week

### Issue #4: Add CPU Limits (30 minutes)

```yaml
# Add to resource-heavy services

taboot-worker:
  deploy:
    resources:
      limits:
        cpus: "4.0"
      reservations:
        cpus: "2.0"

taboot-api:
  deploy:
    resources:
      limits:
        cpus: "1.0"
      reservations:
        cpus: "0.5"

taboot-web:
  deploy:
    resources:
      limits:
        cpus: "0.5"
      reservations:
        cpus: "0.25"
```

**Verify:**
```bash
# Check high CPU usage is limited
docker stats --no-stream taboot-worker
# CPU% should not exceed defined limits
```

---

### Issue #5: Backup Strategy (2 hours)

**Create backup script:**

```bash
#!/bin/bash
# File: backup-taboot.sh
# Run: crontab -e → 0 2 * * * /path/to/backup-taboot.sh

set -e

BACKUP_DIR="/backup/taboot/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "Starting Taboot backup at $(date)"

# PostgreSQL backup
echo "Backing up PostgreSQL..."
docker exec taboot-db pg_dump -U taboot taboot | \
  gzip > "$BACKUP_DIR/postgres_dump.sql.gz"

# Neo4j backup
echo "Backing up Neo4j..."
docker exec taboot-graph neo4j-admin dump \
  --database=neo4j --to=/tmp/neo4j.dump 2>/dev/null || true
docker cp taboot-graph:/tmp/neo4j.dump "$BACKUP_DIR/" 2>/dev/null || true

# Qdrant snapshot
echo "Backing up Qdrant..."
docker exec taboot-vectors \
  curl -X POST http://localhost:6333/snapshots 2>/dev/null || true
docker cp taboot-vectors:/qdrant/storage/snapshots \
  "$BACKUP_DIR/qdrant-snapshots" 2>/dev/null || true

# Clean old backups (keep 30 days)
echo "Cleaning up old backups..."
find /backup/taboot -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true

echo "Backup completed: $BACKUP_DIR"
```

**Install:**
```bash
chmod +x backup-taboot.sh
sudo cp backup-taboot.sh /usr/local/bin/

# Verify with cron
crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-taboot.sh
```

---

## 📊 Monitoring

### Add Docker Stats Monitoring (10 minutes)

```bash
#!/bin/bash
# File: monitor-taboot.sh
# Run: watch -n 5 /path/to/monitor-taboot.sh

echo "=== Taboot Service Status ==="
docker-compose ps

echo ""
echo "=== Resource Usage (Top 5) ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | \
  head -6

echo ""
echo "=== Memory Limits vs Usage ==="
for container in taboot-api taboot-web taboot-db taboot-vectors; do
  LIMIT=$(docker inspect "$container" 2>/dev/null | \
    grep -A10 '"Memory"' | grep '"Memory":' | head -1 | \
    grep -o '[0-9]*' | awk '{printf "%.1f", $1/1024/1024/1024}')
  USAGE=$(docker stats "$container" --no-stream --format "{{.MemUsage}}" 2>/dev/null || echo "N/A")
  echo "$container: $USAGE / ${LIMIT}G"
done

echo ""
echo "=== GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader || \
  echo "nvidia-smi not available"
```

---

## 🧪 Testing Fixes

### Test 1: Verify Port Binding Fix
```bash
#!/bin/bash

echo "Testing port binding security..."

# These should ALL FAIL (good!)
for port in 4201 4202 4205 4206 6333; do
  echo -n "Port $port: "
  nc -zv 0.0.0.0 $port 2>/dev/null && echo "EXPOSED (BAD!)" || echo "✓ Protected"
done

# These should work (local only)
echo ""
echo "Local access (should work):"
psql -h 127.0.0.1 -U taboot -d taboot -c "SELECT version();" 2>/dev/null && \
  echo "✓ PostgreSQL works locally" || \
  echo "✗ PostgreSQL connection failed"
```

### Test 2: Verify Memory Limits
```bash
#!/bin/bash

echo "Verifying memory limits..."

for container in taboot-api taboot-web taboot-db; do
  LIMIT=$(docker inspect "$container" 2>/dev/null | \
    grep '"Memory":' | grep -o '[0-9]*' | head -1)

  if [ "$LIMIT" -gt 0 ]; then
    echo "✓ $container: $(($LIMIT/1024/1024/1024))GB"
  else
    echo "✗ $container: NO LIMIT (needs fixing)"
  fi
done
```

### Test 3: Verify GPU Sharing
```bash
#!/bin/bash

echo "Verifying GPU services can coexist..."

# Ensure all 4 are running
docker-compose up -d taboot-embed taboot-rerank taboot-ollama taboot-vectors

# Wait for healthy
sleep 30

# Check all running
echo "Service Status:"
docker-compose ps | grep taboot-embed
docker-compose ps | grep taboot-rerank
docker-compose ps | grep taboot-ollama
docker-compose ps | grep taboot-vectors

# Check GPU memory
echo ""
echo "GPU Memory Distribution:"
nvidia-smi
```

---

## ✅ Validation Checklist

Use this checklist after each fix:

```
[ ] Database ports bound to 127.0.0.1 only
  [ ] Test: nc -zv localhost 4201 fails

[ ] Memory limits added to all services
  [ ] Test: docker inspect container | grep Memory
  [ ] Test: docker stats shows all under limits

[ ] GPU services can run simultaneously
  [ ] Test: docker ps shows all 4 GPU services running
  [ ] Test: nvidia-smi shows memory distributed

[ ] CPU limits configured
  [ ] Test: under-load service doesn't exceed limit

[ ] Backup script installed
  [ ] Test: /usr/local/bin/backup-taboot.sh runs
  [ ] Test: backup directory created
  [ ] Test: cron job scheduled

[ ] Monitoring script available
  [ ] Test: watch -n 5 /usr/local/bin/monitor-taboot.sh
  [ ] Test: shows all services + resource usage
```

---

## Emergency Recovery

### If OOM Kills Services:
```bash
# 1. Check which service crashed
docker-compose logs --tail=50

# 2. Increase its memory limit
# Edit docker-compose.yaml: limits.memory: 4G → 8G

# 3. Restart
docker-compose down
docker-compose up -d

# 4. Monitor
watch -n 1 'docker stats'
```

### If GPU Service Hangs:
```bash
# 1. Check GPU status
nvidia-smi

# 2. Find stuck container
docker ps | grep taboot

# 3. Restart GPU service
docker restart taboot-embed  # or whichever is stuck

# 4. Verify startup
docker-compose logs taboot-embed | tail -20
```

### If Backup Fails:
```bash
# 1. Check recent backups
ls -lah /backup/taboot/

# 2. Verify PostgreSQL is accessible
docker exec taboot-db pg_isready

# 3. Test backup manually
docker exec taboot-db pg_dump -U taboot taboot > /tmp/test_dump.sql

# 4. Check disk space
df -h | grep backup
```

---

## Documentation Files

- **Full Audit:** `/home/jmagar/code/taboot/docs/INFRASTRUCTURE_AUDIT_REPORT.md`
- **This Guide:** `/home/jmagar/code/taboot/docs/INFRASTRUCTURE_QUICK_FIX_GUIDE.md`

---

## Implementation Tracking

**Week 1 (CRITICAL):**
- [ ] Fix database port exposure
- [ ] Add memory limits
- [ ] Resolve GPU contention

**Week 2 (HIGH):**
- [ ] Add CPU limits
- [ ] Implement backup script
- [ ] Add monitoring

**Month 1 (MEDIUM):**
- [ ] Pin image versions
- [ ] Add Prometheus metrics
- [ ] Create Grafana dashboards

---

**Last Updated:** 2025-10-27
**For:** Taboot single-user RAG platform
**Status:** Ready for implementation
