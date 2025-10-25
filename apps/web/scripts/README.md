# Taboot Data Management Scripts

This directory contains maintenance scripts for the Taboot platform.

## cleanup-deleted-users.ts

Permanently deletes users that have been soft-deleted beyond the retention period (default: 90 days).

### Usage

```bash
# Production cleanup
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts

# Dry run (preview what would be deleted)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --dry-run

# Custom retention period (30 days)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --retention-days=30
```

### Cron Setup

**Daily cleanup at 2 AM:**

```bash
# Edit crontab
crontab -e

# Add this line
0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts >> /var/log/taboot-cleanup.log 2>&1
```

**Weekly cleanup (Sundays at 3 AM):**

```bash
0 3 * * 0 cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts >> /var/log/taboot-cleanup.log 2>&1
```

### Docker/Production Setup

**Using systemd timer (recommended for production):**

Create `/etc/systemd/system/taboot-cleanup.service`:

```ini
[Unit]
Description=Taboot User Cleanup
After=network.target

[Service]
Type=oneshot
User=taboot
WorkingDirectory=/opt/taboot
Environment="NODE_ENV=production"
ExecStart=/usr/bin/pnpm tsx apps/web/scripts/cleanup-deleted-users.ts
StandardOutput=append:/var/log/taboot-cleanup.log
StandardError=append:/var/log/taboot-cleanup.log
```

Create `/etc/systemd/system/taboot-cleanup.timer`:

```ini
[Unit]
Description=Run Taboot User Cleanup Daily
Requires=taboot-cleanup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable taboot-cleanup.timer
sudo systemctl start taboot-cleanup.timer
sudo systemctl status taboot-cleanup.timer
```

**Using Docker Compose:**

Add to `docker-compose.yaml`:

```yaml
services:
  taboot-cleanup:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
    command: sh -c "apk add --no-cache pnpm && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts"
    depends_on:
      - taboot-db
    restart: "no"  # Run via external cron or K8s CronJob
```

Run manually:

```bash
docker compose run --rm taboot-cleanup
```

**Kubernetes CronJob:**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: taboot-cleanup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: taboot:latest
            command:
            - pnpm
            - tsx
            - apps/web/scripts/cleanup-deleted-users.ts
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: taboot-secrets
                  key: database-url
          restartPolicy: OnFailure
```

### Monitoring

**Check last run:**

```bash
tail -n 50 /var/log/taboot-cleanup.log
```

**Verify systemd timer:**

```bash
systemctl list-timers | grep taboot
journalctl -u taboot-cleanup.service -n 50
```

**Alerting on failures (example with healthchecks.io):**

Modify the cron command:

```bash
0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts && curl -fsS -m 10 --retry 5 https://hc-ping.com/your-uuid-here > /dev/null
```

### Safety Features

1. **Dry Run Mode**: Preview deletions without making changes
2. **Interactive Confirmation**: Prompts for confirmation in TTY mode (unless `CI=true`)
3. **Audit Logging**: All hard deletions logged to `AuditLog` table
4. **Error Handling**: Failed deletions don't abort the entire cleanup
5. **Retention Period**: Configurable grace period (default 90 days)

### GDPR Compliance

This script is designed to support GDPR Article 17 (Right to Erasure) requirements:

- **Audit Trail**: All deletions logged with timestamp and retention period
- **Retention Period**: Configurable retention period before permanent deletion
- **User-Initiated**: Original soft delete logs who requested deletion
- **Permanent Deletion**: Final hard delete after retention period expires

### Troubleshooting

**Error: "Cannot find module '@taboot/db'"**

```bash
# Install dependencies first
pnpm install
```

**Error: "Permission denied"**

```bash
# Make script executable
chmod +x apps/web/scripts/cleanup-deleted-users.ts
```

**Script runs but deletes nothing:**

Check if there are users beyond retention period:

```sql
SELECT id, email, deleted_at
FROM "user"
WHERE deleted_at IS NOT NULL
  AND deleted_at < NOW() - INTERVAL '90 days';
```

**Database connection timeout:**

Increase timeout in `DATABASE_URL`:

```bash
DATABASE_URL="postgresql://user:pass@host:5432/db?connect_timeout=30"
```

### Related Documentation

- Soft Delete Implementation: `/home/jmagar/code/taboot/CLAUDE.md` (Data Integrity section)
- Prisma Middleware: `/home/jmagar/code/taboot/packages-ts/db/src/middleware/soft-delete.ts`
- Audit Trail: See `AuditLog` model in Prisma schema
