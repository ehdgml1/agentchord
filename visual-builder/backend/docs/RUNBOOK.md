# Tool Hub Operations Runbook

This document provides operational procedures for running, monitoring, and maintaining the Tool Hub Backend in production environments.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Deployment](#deployment)
3. [Configuration](#configuration)
4. [Monitoring](#monitoring)
5. [Common Operations](#common-operations)
6. [Troubleshooting](#troubleshooting)
7. [Incident Response](#incident-response)
8. [Maintenance](#maintenance)

---

## System Architecture

### Components

**Tool Hub Backend** is a FastAPI application with the following components:

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  API Routers:                                            │
│  ├─ /api/workflows     - Workflow management            │
│  ├─ /api/executions    - Execution tracking             │
│  ├─ /api/schedules     - Cron scheduling                │
│  ├─ /api/mcp/servers   - MCP integration                │
│  ├─ /api/secrets       - Secret management              │
│  ├─ /api/versions      - Version control                │
│  ├─ /webhook           - Incoming webhooks              │
│  └─ /health            - Health probes                  │
│                                                           │
│  Core Services:                                          │
│  ├─ WorkflowScheduler   - APScheduler-based job runner  │
│  ├─ ExecutionService    - Execution tracking            │
│  ├─ WorkflowExecutor    - Node execution engine         │
│  ├─ DebugExecutor       - Debug mode executor           │
│  ├─ MCPManager          - MCP server connections        │
│  ├─ SecretStore         - Encrypted secret storage      │
│  └─ VersionStore        - Workflow versioning           │
│                                                           │
│  Data Layer:                                             │
│  ├─ SQLAlchemy ORM      - Database abstraction          │
│  ├─ Async repositories  - Data access patterns          │
│  └─ Pydantic models     - Data validation               │
│                                                           │
└─────────────────────────────────────────────────────────┘
         ↑                           ↑              ↑
    JWT Auth              Database (SQLite/PostgreSQL)
                          Webhooks (Inbound)
```

### Deployment Models

#### Local Development
- **Database**: SQLite (file-based)
- **Scheduler**: In-process APScheduler
- **Execution**: Synchronous or async
- **MCP**: Local subprocess connections

#### Production Single-Node
- **Database**: PostgreSQL (managed service recommended)
- **Scheduler**: APScheduler with database persistence
- **Execution**: Async with queuing
- **MCP**: Remote subprocess connections
- **Storage**: Persistent volumes for state

#### Production Multi-Node (Future)
- **Database**: PostgreSQL with replication
- **Scheduler**: Distributed APScheduler
- **Execution**: Celery + Redis queue
- **MCP**: Shared connection pool
- **Storage**: Shared network storage

---

## Deployment

### Prerequisites

- **Python**: 3.11 or higher
- **Package Manager**: pip or poetry
- **Database**: SQLite (dev) or PostgreSQL 12+ (prod)
- **Memory**: Minimum 512MB, recommended 2GB
- **CPU**: Single core minimum, 2+ cores recommended

### Installation

#### 1. Clone Repository

```bash
cd /path/to/visual-builder/backend
```

#### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e ../../  # Install agentchord core locally
```

#### 4. Initialize Database

For PostgreSQL:

```bash
export DATABASE_URL="postgresql://user:password@localhost/tool_hub"
alembic upgrade head
```

For SQLite (development):

```bash
export DATABASE_URL="sqlite:///./tool_hub.db"
python -c "from app.db.database import init_db; init_db()"
```

#### 5. Generate JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))" > .jwt_secret
export JWT_SECRET=$(cat .jwt_secret)
```

#### 6. Start Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Systemd Service (Linux)

Create `/etc/systemd/system/tool-hub.service`:

```ini
[Unit]
Description=Tool Hub Backend
After=network.target postgresql.service
StartLimitIntervalSec=200
StartLimitBurst=5

[Service]
Type=notify
User=toolhub
WorkingDirectory=/opt/tool-hub/backend
Environment="PATH=/opt/tool-hub/backend/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="DATABASE_URL=postgresql://toolhub:password@localhost/tool_hub"
Environment="JWT_SECRET_FILE=/opt/tool-hub/secrets/jwt_secret"
Environment="ENVIRONMENT=production"
Environment="CORS_ORIGINS=https://app.example.com"

ExecStart=/opt/tool-hub/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tool-hub
sudo systemctl start tool-hub
sudo systemctl status tool-hub
```

### Docker Deployment

See `Dockerfile` in the repository root for containerized deployment.

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | `sqlite:///./tool_hub.db` | Development only |
| `JWT_SECRET` | JWT signing secret (min 32 chars) | (none) | Yes |
| `ENVIRONMENT` | Deployment environment | `development` | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173,http://localhost:5174` | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `REDIS_URL` | Redis connection for distributed execution | (none) | Optional |
| `MCP_TIMEOUT` | MCP server call timeout (seconds) | `30` | No |
| `EXECUTION_TIMEOUT` | Workflow execution timeout (seconds) | `3600` | No |
| `BATCH_SIZE` | Pagination default batch size | `100` | No |

### JWT Secret Management

**Important**: The JWT secret should be:
- At least 32 characters
- Cryptographically random
- Never committed to version control
- Stored securely (e.g., AWS Secrets Manager, HashiCorp Vault)

Generate a new secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Rotate JWT secret (invalidates existing tokens):

```bash
# 1. Generate new secret
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Update environment
export JWT_SECRET=$NEW_SECRET

# 3. Restart application
sudo systemctl restart tool-hub

# Note: Existing tokens will be invalid
```

### Database Configuration

#### SQLite (Development)

```bash
export DATABASE_URL="sqlite:///./tool_hub.db"
```

#### PostgreSQL (Production)

```bash
export DATABASE_URL="postgresql://user:password@host:5432/tool_hub"
```

Connection pool options:

```bash
# For high-concurrency environments
export DATABASE_URL="postgresql://user:password@host/tool_hub?
pool_size=20&max_overflow=10&pool_pre_ping=true"
```

### CORS Configuration

Allow specific origins:

```bash
export CORS_ORIGINS="https://app.example.com,https://admin.example.com"
```

Allow all origins (development only):

```bash
export CORS_ORIGINS="*"
```

---

## Monitoring

### Health Check Endpoints

All health checks are unauthenticated and suitable for load balancer probes.

#### Liveness Probe

Check if process is running:

```bash
curl http://localhost:8000/health/live
```

Response:
```json
{"status": "alive"}
```

**Configuration** (Kubernetes example):
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

#### Readiness Probe

Check if service is ready to accept traffic:

```bash
curl http://localhost:8000/health/ready
```

Response:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "scheduler": true
  }
}
```

**Configuration** (Kubernetes example):
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

#### MCP Server Health

Check individual MCP server health:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/health/mcp/server-id
```

Response:
```json
{
  "server_id": "server-id",
  "status": "healthy",
  "message": null,
  "latency_ms": 15
}
```

### Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Response Time (p99) | < 500ms | > 1000ms |
| Database Connection Pool | < 80% used | > 90% used |
| Scheduler Job Duration | < 30s | > 60s |
| Execution Success Rate | > 95% | < 90% |
| Active Executions | Varies | > queue_size |
| Memory Usage | < 60% | > 80% |
| Disk Usage (logs) | < 70% | > 85% |

### Logging

Access application logs:

```bash
# View logs (systemd)
sudo journalctl -u tool-hub -f

# View logs (Docker)
docker logs -f tool-hub-container

# View logs (local)
tail -f app.log
```

Adjust log level at runtime:

```bash
export LOG_LEVEL=DEBUG
# Restart application
sudo systemctl restart tool-hub
```

### OpenTelemetry Integration (Future)

When implemented, metrics will be exported to:
- Prometheus endpoint (`/metrics`)
- Jaeger tracing
- ELK stack for log aggregation

---

## Common Operations

### Restart Services

```bash
# Graceful restart (connections drain)
sudo systemctl restart tool-hub

# Force restart (immediate)
sudo systemctl kill -s SIGKILL tool-hub
sudo systemctl start tool-hub

# Reload configuration (without restart)
sudo systemctl reload tool-hub
```

### Clear Execution Queue

View pending executions:

```bash
sqlite3 tool_hub.db "SELECT id, workflow_id, status FROM executions WHERE status='pending' LIMIT 10;"
```

Mark stuck executions as failed:

```bash
sqlite3 tool_hub.db "
UPDATE executions
SET status='failed', error='Manually marked as failed'
WHERE status='running' AND started_at < datetime('now', '-1 hour');
"
```

### Rotate Secrets

Update specific secret value:

```bash
curl -X PUT http://localhost:8000/api/secrets/OPENAI_API_KEY \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "sk-new-api-key"}'
```

Create new secret:

```bash
curl -X POST http://localhost:8000/api/secrets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NEW_SECRET",
    "value": "secret-value",
    "description": "Purpose of this secret"
  }'
```

### Backup Database

#### SQLite

```bash
# Single backup
cp tool_hub.db tool_hub.db.backup.$(date +%Y%m%d-%H%M%S)

# Automated daily backup
0 2 * * * cp /opt/tool-hub/tool_hub.db /backups/tool_hub.db.$(date +\%Y\%m\%d)
```

#### PostgreSQL

```bash
# Manual backup
pg_dump -U toolhub -h localhost tool_hub > tool_hub.sql.$(date +%Y%m%d-%H%M%S)

# With compression
pg_dump -U toolhub -h localhost tool_hub | gzip > tool_hub.sql.gz

# Automated backup (cron)
0 2 * * * pg_dump -U toolhub -h localhost tool_hub | gzip > /backups/tool_hub.sql.$(date +\%Y\%m\%d).gz
```

### Database Maintenance

```bash
# Analyze query performance
ANALYZE;

# Rebuild indexes (SQLite)
REINDEX;

# Vacuum database (SQLite)
VACUUM;

# PostgreSQL maintenance
VACUUM ANALYZE;
REINDEX DATABASE tool_hub;
```

### Scale Horizontally

**For single-node to multi-node migration:**

1. Ensure database is PostgreSQL (not SQLite)
2. Set `REDIS_URL` environment variable for job queue
3. Add new application nodes with same configuration
4. Update load balancer to distribute traffic
5. Configure distributed scheduler (APScheduler with database backend)

```bash
# Node 1-N configuration
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://redis-cluster:6379"
export SCHEDULER_MODE="distributed"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Troubleshooting

### Issue: API Returns 500 on Every Request

**Symptoms**: All requests return `{"error": {"code": "INTERNAL_ERROR"}}`

**Diagnosis**:
```bash
# Check logs
sudo journalctl -u tool-hub -n 50

# Check database connectivity
sqlite3 tool_hub.db "SELECT 1;"

# Verify JWT secret is set
echo $JWT_SECRET
```

**Resolution**:
1. Check database file exists and is readable
2. Verify JWT_SECRET environment variable is set
3. Check disk space: `df -h`
4. Restart service: `sudo systemctl restart tool-hub`

### Issue: Scheduler Not Executing Jobs

**Symptoms**: Scheduled workflows don't run at scheduled times

**Diagnosis**:
```bash
# Check if scheduler is running
curl http://localhost:8000/health/ready | jq '.checks.scheduler'

# View scheduled jobs
sqlite3 tool_hub.db "SELECT id, name, next_run_time FROM apscheduler_jobs LIMIT 5;"

# Check scheduler logs
sudo journalctl -u tool-hub -k scheduler
```

**Resolution**:
1. Verify scheduler service started: `sudo systemctl status tool-hub`
2. Check cron expression validity: `croniter -v "0 9 * * *"`
3. Ensure workflow exists: `sqlite3 tool_hub.db "SELECT id FROM workflows WHERE id='workflow-id';"`
4. Restart scheduler: `sudo systemctl restart tool-hub`

### Issue: Execution Stuck in "Running" State

**Symptoms**: Execution shows "running" but no progress for > 1 hour

**Diagnosis**:
```bash
# Find stuck execution
sqlite3 tool_hub.db "
SELECT id, workflow_id, status, started_at, updated_at
FROM executions
WHERE status='running' AND updated_at < datetime('now', '-1 hour');
"

# Check executor logs for errors
sudo journalctl -u tool-hub | grep -A 5 "execution-id"
```

**Resolution**:
1. Check MCP server health: `curl http://localhost:8000/health/mcp/server-id`
2. If MCP server is down, restart it
3. Stop the stuck execution:
   ```bash
   curl -X POST http://localhost:8000/api/executions/execution-id/stop \
     -H "Authorization: Bearer $TOKEN"
   ```
4. Investigate root cause in logs
5. If workflow is unrecoverable, manually mark as failed:
   ```bash
   sqlite3 tool_hub.db "
   UPDATE executions
   SET status='failed', error='Stuck execution - manually stopped'
   WHERE id='execution-id';
   "
   ```

### Issue: MCP Server Won't Connect

**Symptoms**: `SERVER_NOT_FOUND` or "connection refused" errors

**Diagnosis**:
```bash
# Verify MCP server is running
ps aux | grep mcp-server

# Test MCP server directly
mcp --version

# Check network connectivity
nc -zv mcp-server-host 1234

# View MCP manager logs
sudo journalctl -u tool-hub | grep -i mcp
```

**Resolution**:
1. Ensure MCP server process is running
2. Check MCP server configuration in database:
   ```bash
   sqlite3 tool_hub.db "SELECT id, name, command, status FROM mcp_servers;"
   ```
3. Reconnect MCP server:
   ```bash
   curl -X DELETE http://localhost:8000/api/mcp/servers/server-id \
     -H "Authorization: Bearer $TOKEN"

   curl -X POST http://localhost:8000/api/mcp/servers \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "server-name", "command": "...", "args": [...]}'
   ```

### Issue: Database Connection Pool Exhausted

**Symptoms**: `QueuePool timeout - connection pool is exhausted`

**Diagnosis**:
```bash
# Check active connections (PostgreSQL)
psql -U toolhub -c "SELECT count(*) FROM pg_stat_activity;"

# View connection pool stats
curl http://localhost:8000/health/ready | jq '.database'
```

**Resolution**:
1. Increase pool size in DATABASE_URL
2. Reduce long-running queries
3. Kill idle connections:
   ```bash
   psql -U toolhub -c "
   SELECT pg_terminate_backend(pg_stat_activity.pid)
   FROM pg_stat_activity
   WHERE state='idle' AND query_start < now() - interval '5 minutes';
   "
   ```
4. Restart application: `sudo systemctl restart tool-hub`

### Issue: High Memory Usage

**Symptoms**: Process using > 80% available RAM

**Diagnosis**:
```bash
# Monitor memory in real-time
watch -n 1 'ps aux | grep uvicorn | head -1'

# Check for memory leaks
python -m memory_profiler app.main
```

**Resolution**:
1. Reduce worker count: `--workers 2` (instead of 4)
2. Lower batch size: `--batch-size 50` (instead of 100)
3. Restart application to clear caches: `sudo systemctl restart tool-hub`
4. If persists, investigate for memory leaks in custom code

---

## Incident Response

### Severity Levels

| Level | Impact | Response Time |
|-------|--------|----------------|
| **Critical** | Complete service outage, data loss risk | 15 minutes |
| **High** | Partial service degradation, execution failures | 30 minutes |
| **Medium** | Performance degradation, some requests failing | 2 hours |
| **Low** | Minor issues, workarounds exist | 8 hours |

### Incident Escalation

```
On-Call Engineer → Team Lead → Engineering Manager
     (15 min)         (30 min)      (60 min)
```

### Critical Incident Checklist

**Immediate (0-5 min)**:
- [ ] Acknowledge incident
- [ ] Assess impact (# of users affected, service availability)
- [ ] Page on-call team if needed
- [ ] Create incident ticket with ID

**Triage (5-15 min)**:
- [ ] Determine if emergency restart needed
- [ ] Check health endpoints
- [ ] Review recent deployments
- [ ] Check infrastructure status
- [ ] Communicate status to stakeholders

**Recovery (15-60 min)**:
- [ ] Implement fix or rollback
- [ ] Monitor recovery metrics
- [ ] Verify service is stable
- [ ] Update incident ticket

**Post-Incident (within 24h)**:
- [ ] Complete root cause analysis
- [ ] Identify preventive measures
- [ ] Schedule follow-up actions
- [ ] Document incident in runbook

### Common Incident Scenarios

#### Complete Service Outage

```bash
# 1. Check service status
sudo systemctl status tool-hub

# 2. View recent errors
sudo journalctl -u tool-hub -n 100

# 3. Quick fix attempt (restart)
sudo systemctl restart tool-hub

# 4. If restart fails, check logs for startup errors
sudo journalctl -u tool-hub -e

# 5. If database issue, verify connectivity
sqlite3 tool_hub.db "SELECT 1;" || psql -c "SELECT 1;"

# 6. If unfixable, switch to backup/standby system
# (Contact infrastructure team)
```

#### Cascading Execution Failures

```bash
# 1. Stop new execution submissions
# (Temporarily disable API if needed)

# 2. Find failed executions
sqlite3 tool_hub.db "
SELECT id, workflow_id, error FROM executions
WHERE status='failed' AND created_at > datetime('now', '-1 hour');
"

# 3. Check if common error exists
# (e.g., MCP server down, secret missing)

# 4. Fix underlying issue
# (Restart MCP server, update secret, etc.)

# 5. Manually retry failed executions
curl -X POST http://localhost:8000/api/executions/id/resume \
  -H "Authorization: Bearer $TOKEN"

# 6. Re-enable API
```

#### Database Corruption

```bash
# 1. Stop application
sudo systemctl stop tool-hub

# 2. Backup corrupted database
cp tool_hub.db tool_hub.db.corrupted.$(date +%s)

# 3. Restore from backup
cp /backups/tool_hub.db.20240105 tool_hub.db

# 4. Verify integrity
sqlite3 tool_hub.db "PRAGMA integrity_check;"

# 5. Restart application
sudo systemctl start tool-hub

# 6. Verify functionality
curl http://localhost:8000/health/ready
```

---

## Maintenance

### Regular Maintenance Schedule

| Task | Frequency | Estimated Time |
|------|-----------|-----------------|
| Backup database | Daily | 5 min |
| Review error logs | Daily | 10 min |
| Update dependencies | Weekly | 30 min |
| Clear old execution logs | Weekly | 5 min |
| Database optimization | Monthly | 15 min |
| Security audit | Quarterly | 2 hours |
| Capacity planning | Quarterly | 1 hour |

### Database Cleanup

Remove old executions (retain 90 days):

```bash
sqlite3 tool_hub.db "
DELETE FROM node_logs
WHERE execution_id IN (
  SELECT id FROM executions
  WHERE completed_at < datetime('now', '-90 days')
);

DELETE FROM executions
WHERE completed_at < datetime('now', '-90 days');
"
```

### Dependency Updates

```bash
# Check for updates
pip list --outdated

# Update all dependencies
pip install -U -r requirements.txt

# Run tests to verify
pytest tests/ -v

# Restart application
sudo systemctl restart tool-hub
```

### Performance Tuning

#### Database Query Performance

Enable query logging:

```bash
export SQL_ECHO=true
# Restart application
```

Analyze slow queries:

```bash
# SQLite
sqlite3 tool_hub.db "EXPLAIN QUERY PLAN SELECT ..."

# PostgreSQL
EXPLAIN ANALYZE SELECT ...;
```

Add indexes for common queries:

```sql
-- Execution queries
CREATE INDEX idx_executions_workflow_id ON executions(workflow_id);
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_created_at ON executions(created_at);

-- Node logs queries
CREATE INDEX idx_node_logs_execution_id ON node_logs(execution_id);
CREATE INDEX idx_node_logs_node_id ON node_logs(node_id);
```

#### API Response Optimization

- Enable caching for workflow definitions
- Paginate large result sets
- Use database connection pooling
- Implement query result compression

### Capacity Planning

Monitor these metrics monthly:

```bash
# Database size
du -sh tool_hub.db

# Number of workflows
sqlite3 tool_hub.db "SELECT COUNT(*) FROM workflows;"

# Number of executions
sqlite3 tool_hub.db "SELECT COUNT(*) FROM executions;"

# Disk usage trend
df -h | grep -E "tool_hub|total"
```

Estimate growth:

```
If growing 10GB/month:
- Current: 50GB
- 1 year projection: 170GB
- Recommend: Start archival/cleanup at 100GB
```

---

## Support and Escalation

### Get Help

- **Documentation**: Check `/docs` (Swagger UI) or `/redoc`
- **Logs**: Review `journalctl -u tool-hub`
- **Database**: Query directly for investigation
- **Community**: File issues in repository

### Escalation Contacts

| Role | Contact | Response Time |
|------|---------|----------------|
| On-Call | Page via PagerDuty | 15 min |
| Team Lead | Slack: @lead | 30 min |
| Database Admin | Slack: #database | 1 hour |
| Infrastructure | Slack: #infrastructure | 2 hours |

### Emergency Contacts

Document emergency contacts in a separate, secure location:
- On-call phone
- Manager contact
- CTO contact
- Infrastructure team lead

---

## Appendix

### Useful Commands

```bash
# Check service status
sudo systemctl status tool-hub

# View recent logs (50 lines)
sudo journalctl -u tool-hub -n 50

# Follow logs in real-time
sudo journalctl -u tool-hub -f

# View logs for specific time period
sudo journalctl -u tool-hub --since "2 hours ago"

# List all workflows
sqlite3 tool_hub.db "SELECT id, name FROM workflows LIMIT 10;"

# List active executions
sqlite3 tool_hub.db "SELECT id, workflow_id, status FROM executions WHERE status IN ('pending', 'running');"

# Get execution details
sqlite3 tool_hub.db "SELECT * FROM executions WHERE id='exec-id';"

# Check JWT secret is valid
curl -X GET http://localhost:8000/health/live

# Test API endpoint with auth
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/workflows
```

### Environment Setup Script

Save as `setup_prod_env.sh`:

```bash
#!/bin/bash
set -e

# Tool Hub Production Environment Setup

echo "=== Tool Hub Backend Setup ==="

# 1. Create service user
sudo useradd -r -s /bin/bash toolhub || true

# 2. Create directories
sudo mkdir -p /opt/tool-hub/backend
sudo mkdir -p /opt/tool-hub/secrets
sudo mkdir -p /var/log/tool-hub
sudo mkdir -p /var/lib/tool-hub

# 3. Set permissions
sudo chown -R toolhub:toolhub /opt/tool-hub
sudo chown -R toolhub:toolhub /var/log/tool-hub
sudo chown -R toolhub:toolhub /var/lib/tool-hub

# 4. Generate JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "$JWT_SECRET" | sudo tee /opt/tool-hub/secrets/jwt_secret > /dev/null
sudo chmod 600 /opt/tool-hub/secrets/jwt_secret
sudo chown toolhub:toolhub /opt/tool-hub/secrets/jwt_secret

echo "JWT Secret generated: $JWT_SECRET"

# 5. Setup logrotate
sudo tee /etc/logrotate.d/tool-hub > /dev/null <<EOF
/var/log/tool-hub/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    postrotate
        systemctl reload tool-hub > /dev/null 2>&1 || true
    endscript
}
EOF

echo "Setup complete!"
echo "Next: Install requirements and start service"
```

---

**Document Version**: 1.0
**Last Updated**: 2024-01-15
**Maintained By**: Backend Operations Team
