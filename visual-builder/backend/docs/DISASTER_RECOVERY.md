# Disaster Recovery Procedures

This document outlines procedures for preventing, detecting, and recovering from catastrophic failures of Tool Hub services.

## Table of Contents

1. [Overview](#overview)
2. [Backup Strategy](#backup-strategy)
3. [Recovery Procedures](#recovery-procedures)
4. [RTO/RPO Targets](#rtorpo-targets)
5. [Failover Procedures](#failover-procedures)
6. [Testing and Validation](#testing-and-validation)

---

## Overview

### Disaster Types

| Disaster | Cause | Recovery Time |
|----------|-------|----------------|
| **Data Corruption** | Bug, hardware failure | 30 minutes |
| **Single Node Failure** | Server crash, hardware | 15 minutes |
| **Database Failure** | Disk failure, corruption | 1-4 hours |
| **Network Partition** | ISP outage, DNS failure | 5-30 minutes |
| **Region Failure** | Data center outage | 2-24 hours |
| **Complete Loss** | Fire, disaster | 24+ hours |

### Recovery Priority

1. **Restore data integrity** - Ensure no data loss beyond acceptable RPO
2. **Restore service availability** - Get API responding to requests
3. **Restore automation** - Re-enable scheduled executions
4. **Verify completeness** - Ensure all components operational
5. **Communicate** - Update stakeholders on status

---

## Backup Strategy

### What to Backup

#### Critical Data (RPO: 1 hour)
- **Database** - All workflows, executions, schedules, secrets
- **Secrets** - Encrypted copies of secret values
- **Configuration** - Environment variables, settings

#### Important Data (RPO: 24 hours)
- **Application Code** - Source code, dependencies
- **Execution Logs** - Historical execution details
- **Audit Logs** - Compliance and audit trail

#### Non-Critical Data (RPO: 7 days)
- **Metrics** - Performance and usage statistics
- **Cache** - Computed results (can be regenerated)

### Database Backups

#### Full Backup (Daily)

**SQLite**:
```bash
#!/bin/bash
# Backup to S3

BACKUP_DIR="/backups/tool_hub"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/tool_hub_full_$TIMESTAMP.db"

mkdir -p $BACKUP_DIR

# Stop ongoing backups
cd /var/lib/tool-hub
sqlite3 tool_hub.db "PRAGMA main.synchronous = NORMAL;"

# Backup database
sqlite3 tool_hub.db ".backup $BACKUP_FILE"

# Compress and upload to S3
gzip -9 "$BACKUP_FILE"
aws s3 cp "$BACKUP_FILE.gz" s3://backups/tool-hub/ --storage-class GLACIER

# Retain local copy for 7 days
find $BACKUP_DIR -name "tool_hub_full_*.db.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_FILE.gz"
```

**PostgreSQL**:
```bash
#!/bin/bash
# Daily full backup

BACKUP_DIR="/backups/tool_hub"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/tool_hub_full_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

# Full backup
pg_dump -U toolhub -h localhost -F custom -b -v -f "$BACKUP_FILE" tool_hub

# Compress
gzip -9 "$BACKUP_FILE"

# Upload to S3
aws s3 cp "$BACKUP_FILE.gz" s3://backups/tool-hub/ --storage-class GLACIER

# Retain local for 7 days
find $BACKUP_DIR -name "tool_hub_full_*.sql.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_FILE.gz"
```

Add to crontab:
```bash
# 2 AM daily
0 2 * * * /opt/tool-hub/scripts/backup-full.sh
```

#### Incremental Backup (Hourly)

**PostgreSQL WAL Archiving**:
```bash
# In postgresql.conf
archive_mode = on
archive_command = 'test ! -f /backups/wal/%f && cp %p /backups/wal/%f'
archive_timeout = 300

# Clean old WAL files (older than 7 days)
0 * * * * find /backups/wal -mtime +7 -delete
```

#### Backup Verification

Test backup restoration weekly:

```bash
#!/bin/bash
# Verify backup integrity

BACKUP_FILE="/backups/tool_hub/tool_hub_full_latest.sql.gz"
TEST_DB="test_tool_hub"

# Create test database
createdb $TEST_DB

# Restore from backup
gunzip -c "$BACKUP_FILE" | psql -U toolhub -d $TEST_DB

# Verify data
WORKFLOW_COUNT=$(psql -U toolhub -d $TEST_DB -t -c "SELECT COUNT(*) FROM workflows;")
EXECUTION_COUNT=$(psql -U toolhub -d $TEST_DB -t -c "SELECT COUNT(*) FROM executions;")

if [[ $WORKFLOW_COUNT -gt 0 ]] && [[ $EXECUTION_COUNT -gt 0 ]]; then
    echo "Backup verification SUCCESS"
    echo "Workflows: $WORKFLOW_COUNT"
    echo "Executions: $EXECUTION_COUNT"
else
    echo "Backup verification FAILED"
    exit 1
fi

# Cleanup
dropdb $TEST_DB
```

### Secret Key Backup

**Critical**: Store encrypted copies of secrets securely.

```bash
# Backup JWT secret (encrypted)
openssl enc -aes-256-cbc -salt \
  -in /opt/tool-hub/secrets/jwt_secret \
  -out /backups/secrets/jwt_secret.enc \
  -k "encryption-passphrase"

# Store encryption passphrase in secure location (separate from backup)
# (e.g., password manager, HSM, printed in envelope)

# Backup API secrets
sqlite3 /var/lib/tool-hub/tool_hub.db \
  "SELECT name, value FROM secrets;" | \
  openssl enc -aes-256-cbc -salt \
  -out /backups/secrets/api_secrets.enc \
  -k "encryption-passphrase"
```

### Configuration Backup

```bash
#!/bin/bash
# Backup configuration files

BACKUP_DIR="/backups/config"
mkdir -p $BACKUP_DIR

# Backup systemd service file
cp /etc/systemd/system/tool-hub.service $BACKUP_DIR/

# Backup environment file (sanitized)
cp /opt/tool-hub/.env $BACKUP_DIR/.env.backup

# Backup database configuration
pg_dumpall -U postgres --roles-only > $BACKUP_DIR/pg_roles.sql

# Upload to S3
aws s3 sync $BACKUP_DIR s3://backups/tool-hub/config/
```

### Backup Storage

**3-2-1 Backup Rule**: 3 copies, 2 media types, 1 offsite

```
Local (daily)          → 7-day retention
└─ /backups/tool-hub

Secondary (daily)      → 30-day retention
└─ S3 Standard

Archive (weekly)       → 1-year retention
└─ S3 Glacier
```

**Backup Schedule**:

| Type | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| Full Database | Daily (2 AM) | 30 days | Local + S3 |
| WAL Archives | Hourly | 7 days | Local + S3 |
| Secrets (encrypted) | Weekly | 1 year | Local + Vault |
| Configuration | Weekly | 1 year | Local + S3 |
| Full System | Monthly | 1 year | S3 Glacier |

---

## Recovery Procedures

### Recovery from Single Node Failure

**Scenario**: Server crashes, needs to be rebuilt

**RTO**: 15 minutes | **RPO**: 1 hour

**Steps**:

1. **Alert and Assessment** (1 min)
   ```bash
   # Health check fails, alert fires
   # Check status
   ping tool-hub-server.internal
   # No response → Node is down
   ```

2. **Failover** (2 min)
   - Route traffic to backup node (via load balancer)
   - Verify API is responding on backup
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     https://app.example.com/api/workflows
   ```

3. **Rebuild Original Node** (10 min)
   - Terminate failed instance
   - Launch new instance with same configuration
   - Wait for instance to be healthy
   - Add back to load balancer pool

4. **Verification** (2 min)
   - Monitor error rate returns to baseline
   - Verify no data loss
   - Document incident

### Recovery from Database Failure

**Scenario**: Database is corrupted or inaccessible

**RTO**: 1-4 hours | **RPO**: 1 hour

#### Scenario A: Database is Responding But Corrupted

```bash
#!/bin/bash
# Detect corruption
sqlite3 tool_hub.db "PRAGMA integrity_check;"
# Output: "corruption detected in index xyz"

# 1. Stop application
sudo systemctl stop tool-hub

# 2. Backup corrupted database
cp /var/lib/tool-hub/tool_hub.db \
   /backups/tool_hub.db.corrupted.$(date +%s)

# 3. Find latest good backup
LATEST_BACKUP=$(ls -1t /backups/tool_hub_full_*.sql.gz | head -1)
echo "Restoring from: $LATEST_BACKUP"

# 4. Restore database
gunzip -c "$LATEST_BACKUP" | psql -U toolhub -d tool_hub

# 5. Rebuild corrupted indexes
psql -U toolhub -d tool_hub "REINDEX DATABASE tool_hub;"

# 6. Verify integrity
psql -U toolhub -d tool_hub "SELECT COUNT(*) FROM workflows;"

# 7. Start application
sudo systemctl start tool-hub

# 8. Monitor for issues
sudo journalctl -u tool-hub -f
```

#### Scenario B: Database Server is Down

```bash
#!/bin/bash
# 1. Identify issue
# (Hardware failure? Out of disk? Network?)

# 2. If disk failure - provision new database server
#    If recoverable - restart PostgreSQL service

# 3. Check backup status
ls -lh /backups/tool_hub/tool_hub_full_*.sql.gz | head -5

# 4. If no recent backup, check WAL archives
ls -1 /backups/wal/ | tail -20

# 5. Restore latest backup
createdb tool_hub_restore
gunzip -c /backups/tool_hub/tool_hub_full_20240115.sql.gz | \
  psql -U toolhub -d tool_hub_restore

# 6. Replay WAL archives (if available)
pg_wal_replay /backups/wal/ tool_hub_restore

# 7. Verify restored data
psql -U toolhub -d tool_hub_restore "
  SELECT COUNT(*) as workflows FROM workflows;
  SELECT COUNT(*) as executions FROM executions;
"

# 8. Swap database
psql -U postgres "DROP DATABASE IF EXISTS tool_hub;"
psql -U postgres "ALTER DATABASE tool_hub_restore RENAME TO tool_hub;"

# 9. Restart application
sudo systemctl start tool-hub
```

### Recovery from Network Outage

**Scenario**: Network connectivity lost for 30+ minutes

**RTO**: 5-30 minutes | **RPO**: 0 (no data loss)

```bash
#!/bin/bash
# Network issues detected:
# - DNS resolution fails
# - Database unreachable
# - MCP servers unreachable

# 1. Check network status
curl -I https://example.com  # Internet connectivity
dns-test.example.com         # DNS resolution
ping database.internal       # Database connectivity

# 2. Verify local services are running
sudo systemctl status tool-hub
sudo systemctl status postgresql

# 3. Restart network if needed
sudo systemctl restart networking
sudo systemctl restart docker  # If using Docker

# 4. Reconnect MCP servers
curl -X POST http://localhost:8000/api/mcp/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  }'

# 5. Resume suspended executions
curl -X POST http://localhost:8000/api/executions/$EXEC_ID/resume \
  -H "Authorization: Bearer $TOKEN"

# 6. Verify recovery
curl http://localhost:8000/health/ready
```

### Complete System Recovery

**Scenario**: Multiple component failures, need full rebuild

**RTO**: 2-24 hours | **RPO**: 1 hour

#### Phase 1: Infrastructure Setup (30-60 min)

```bash
#!/bin/bash
# 1. Provision new infrastructure
#    - New database server (PostgreSQL)
#    - New application servers (2x)
#    - New load balancer
#    - New backup storage

# 2. Setup networking
#    - Configure VPC/subnets
#    - Setup security groups
#    - Configure DNS
#    - Verify connectivity

# 3. Initialize base systems
#    - Install OS packages
#    - Configure monitoring
#    - Setup logging
#    - Configure backups
```

#### Phase 2: Database Recovery (30-60 min)

```bash
#!/bin/bash
# 1. Restore database from backup
BACKUP_FILE="/backups/tool_hub/tool_hub_full_latest.sql.gz"
gunzip -c "$BACKUP_FILE" | psql -U toolhub

# 2. Restore secrets
# (From encrypted backup, provide passphrase)
openssl enc -d -aes-256-cbc \
  -in /backups/secrets/api_secrets.enc \
  -out /tmp/secrets.sql \
  -k "encryption-passphrase"

psql -U toolhub -d tool_hub < /tmp/secrets.sql
rm /tmp/secrets.sql

# 3. Verify database integrity
psql -U toolhub -d tool_hub "
  SELECT
    (SELECT COUNT(*) FROM workflows) as workflows,
    (SELECT COUNT(*) FROM executions) as executions,
    (SELECT COUNT(*) FROM secrets) as secrets;
"
```

#### Phase 3: Application Deployment (30-45 min)

```bash
#!/bin/bash
# 1. Deploy application code
git clone <repo> /opt/tool-hub/backend
cd /opt/tool-hub/backend
git checkout <release-tag>

# 2. Install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Restore secrets and configuration
cp /backups/secrets/jwt_secret /opt/tool-hub/secrets/
cp /backups/config/.env.backup /opt/tool-hub/.env

# 4. Verify application health
./venv/bin/python -m pytest tests/ -v

# 5. Start application
sudo systemctl start tool-hub
sudo systemctl enable tool-hub
```

#### Phase 4: Validation (15-30 min)

```bash
#!/bin/bash
# 1. Health checks
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# 2. API functionality
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -d '{"user": "admin", "password": "xxx"}' | jq -r '.token')

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workflows

# 3. Database connectivity
sqlite3 /var/lib/tool-hub/tool_hub.db "SELECT COUNT(*) FROM workflows;"

# 4. Scheduler functionality
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/schedules

# 5. MCP server connectivity
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/mcp/servers

# 6. Run test execution
curl -X POST http://localhost:8000/api/workflows/test-workflow/run \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"input": "test"}'
```

---

## RTO/RPO Targets

### Recovery Time Objectives (RTO)

| Failure Type | RTO Target | Notes |
|--------------|-----------|-------|
| Single node crash | 15 min | Automatic failover to backup |
| Database failure | 1-4 hours | Depends on backup freshness |
| Network outage | 5-30 min | Depends on ISP recovery |
| Data corruption | 30 min | Restore from backup + verification |
| Region failure | 2-24 hours | Manual failover to DR region |
| Complete loss | 24+ hours | Full rebuild from backup + config |

### Recovery Point Objectives (RPO)

| Data Type | RPO Target | Backup Frequency |
|-----------|-----------|------------------|
| Workflows | 24 hours | Daily (full) |
| Executions | 1 hour | Hourly (incremental) |
| Secrets | 1 hour | Daily (encrypted) |
| Configuration | 24 hours | Weekly |
| Audit logs | 7 days | Daily |

### Current SLA Commitments

- **Availability**: 99.5% uptime (21.9 hours downtime/month)
- **RTO**: 1 hour maximum for any failure
- **RPO**: 1 hour maximum data loss

---

## Failover Procedures

### Active-Passive Failover (Single to Backup)

**Prerequisite**: Backup instance running in standby

**Steps**:

1. **Detection** (Automated)
   ```bash
   # Health check failure detected
   # Alert triggered, failover initiated
   ```

2. **Health Verification** (30 seconds)
   ```bash
   # Primary down?
   curl -m 5 http://primary.tool-hub/health/live
   # Fails → Proceed to failover
   ```

3. **DNS Update** (1-2 min)
   ```bash
   # Update DNS to point to backup
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z123 \
     --change-batch '{
       "Changes": [{
         "Action": "UPSERT",
         "ResourceRecordSet": {
           "Name": "app.example.com",
           "Type": "A",
           "TTL": 60,
           "ResourceRecords": [{"Value": "10.0.2.100"}]
         }
       }]
     }'
   ```

4. **Load Balancer Update** (1 min)
   ```bash
   # Remove primary from load balancer
   aws elbv2 deregister-targets \
     --target-group-arn $PRIMARY_TG \
     --targets Id=primary-instance

   # Add backup to load balancer
   aws elbv2 register-targets \
     --target-group-arn $PRIMARY_TG \
     --targets Id=backup-instance
   ```

5. **Verification** (2 min)
   ```bash
   # Verify traffic flowing to backup
   curl http://app.example.com/health/live
   # Should respond from backup instance

   # Monitor error rate
   # Should return to baseline within 30 seconds
   ```

6. **Restore Primary** (Ongoing)
   ```bash
   # Investigate failure
   # Rebuild or repair primary
   # Add back to load balancer once fixed
   ```

### Database Failover (PostgreSQL Streaming Replication)

**Prerequisite**: PostgreSQL standby running in continuous recovery

**Setup (One-time)**:

```bash
# Primary server configuration
# In postgresql.conf
max_wal_senders = 10
wal_keep_size = 1GB
hot_standby_feedback = on

# Create replication user
createuser -U postgres replication_user --replication

# Standby initialization
pg_basebackup -h primary.db -U replication_user -D /var/lib/postgresql/data

# Standby configuration
# In recovery.conf
primary_conninfo = 'host=primary.db user=replication_user'
```

**Failover (When Primary is Down)**:

```bash
#!/bin/bash
# 1. Verify primary is truly down
pg_isready -h primary.db -p 5432
# Returns: "accepting connections" or timeout

# 2. Promote standby to primary
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/data

# 3. Verify promotion
psql -c "SELECT pg_is_in_recovery();"
# Should return: f (false - no longer in recovery)

# 4. Update application connection string
export DATABASE_URL="postgresql://toolhub@standby.db/tool_hub"

# 5. Restart application
sudo systemctl restart tool-hub

# 6. Promote new standby (if available)
# Create new standby from promoted primary
```

### Application Layer Failover

**Manual Failover to Secondary Instance**:

```bash
#!/bin/bash
# When primary application instance is stuck/hung

# 1. Stop primary (prevent split-brain)
ssh primary "sudo systemctl stop tool-hub"

# 2. Verify database is accessible from secondary
mysql -h database.internal -u toolhub -p "SELECT 1;"

# 3. Start secondary instance
ssh secondary "sudo systemctl start tool-hub"

# 4. Update DNS to point to secondary
# (Use load balancer or DNS failover)

# 5. Verify functionality
curl -H "Authorization: Bearer $TOKEN" \
  https://app.example.com/api/workflows
```

---

## Testing and Validation

### Quarterly Disaster Recovery Drill

**Schedule**: First Friday of each quarter

**Duration**: 2 hours

**Participants**: DevOps, DBA, Backend Team Lead

**Procedure**:

1. **Simulate Database Failure** (30 min)
   ```bash
   # Scenario: Database server is down
   # Action: Restore database from backup to test environment
   # Validate: Verify data integrity
   ```

2. **Simulate Node Failure** (30 min)
   ```bash
   # Scenario: Application server crashes
   # Action: Failover to backup instance
   # Validate: Traffic flows to backup, no errors
   ```

3. **Simulate Network Failure** (30 min)
   ```bash
   # Scenario: Network partition
   # Action: Re-establish connectivity
   # Validate: Services resume normally
   ```

4. **Document Results** (5 min)
   ```
   Date: Q1 2024
   Scenario: Database failure simulation
   RTO Achieved: 1 hour 15 minutes
   RPO Achieved: 30 minutes
   Issues: [List any issues discovered]
   Actions: [List improvements needed]
   ```

### Backup Verification Checklist

Monthly, verify backups are usable:

```bash
#!/bin/bash
# Backup Verification Test

echo "=== Backup Verification ==="

# 1. Check backup file exists and is readable
BACKUP_FILE="/backups/tool_hub/tool_hub_full_latest.sql.gz"
if [[ -r "$BACKUP_FILE" ]]; then
    echo "✓ Backup file exists and is readable"
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "  Size: $SIZE"
else
    echo "✗ Backup file missing or unreadable"
    exit 1
fi

# 2. Verify backup integrity
if gunzip -t "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "✓ Backup file integrity OK"
else
    echo "✗ Backup file is corrupted"
    exit 1
fi

# 3. Test restore to test database
createdb test_tool_hub_verify || dropdb test_tool_hub_verify && createdb test_tool_hub_verify
gunzip -c "$BACKUP_FILE" | psql -U toolhub -d test_tool_hub_verify

# 4. Verify data
WORKFLOW_COUNT=$(psql -U toolhub -t -d test_tool_hub_verify -c "SELECT COUNT(*) FROM workflows;")
if [[ $WORKFLOW_COUNT -gt 0 ]]; then
    echo "✓ Data restored successfully"
    echo "  Workflows: $WORKFLOW_COUNT"
else
    echo "✗ Restore failed - no data found"
    exit 1
fi

# 5. Cleanup
dropdb test_tool_hub_verify

echo "✓ All backup verification checks passed"
```

### Recovery Documentation

For each disaster recovery event, document:

- **Date/Time**: When disaster occurred
- **Root Cause**: What went wrong
- **Duration**: Time to detect, RTO, total downtime
- **Impact**: Number of affected users, data loss
- **Resolution**: Steps taken to recover
- **Improvements**: Changes to prevent recurrence
- **Lessons Learned**: What we can improve

**Template**:

```markdown
# Incident Report: [Incident ID]

## Summary
One-line summary of the incident.

## Timeline
- 14:32 - Alert: Database connection pool exhausted
- 14:33 - Investigation: Found 500 stuck connections
- 14:45 - Action: Restarted database service
- 14:50 - Resolution: Service restored
- 15:00 - All-clear: Systems verified stable

## Root Cause
[Detailed explanation of what caused the incident]

## Impact
- Users Affected: ~500
- Duration: 18 minutes
- Data Loss: 0
- Services Down: API + Dashboard

## Recovery Actions
1. [Action 1]
2. [Action 2]
3. [Action 3]

## Preventive Measures
1. [Prevention 1]
2. [Prevention 2]
3. [Prevention 3]

## Follow-up Items
- [ ] Implement connection pool monitoring
- [ ] Set lower connection timeout
- [ ] Add automated remediation

## Lessons Learned
[Key learnings from this incident]
```

---

## Appendix

### Key Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-Call | [Name] | [Phone] | [Email] |
| DBA | [Name] | [Phone] | [Email] |
| Infrastructure | [Name] | [Phone] | [Email] |
| Manager | [Name] | [Phone] | [Email] |

### Important Locations

- **Backup Storage**: `s3://backups/tool-hub/`
- **Backup Verification**: `/opt/tool-hub/scripts/verify-backup.sh`
- **Recovery Scripts**: `/opt/tool-hub/scripts/recover-*`
- **Documentation**: `/opt/tool-hub/docs/`

### Useful Commands

```bash
# Check backup freshness
ls -lh /backups/tool_hub/tool_hub_full_*.sql.gz | head -5

# Estimate recovery time
du -sh /backups/tool_hub/tool_hub_full_latest.sql.gz

# Test restore speed
time gunzip -c /backups/tool_hub_full_latest.sql.gz | \
  psql -U toolhub -d test_restore > /dev/null

# Verify all backups
ls /backups/tool_hub/ | wc -l
find /backups/tool_hub -type f -exec gunzip -t {} \;
```

---

**Document Version**: 1.0
**Last Updated**: 2024-01-15
**Maintained By**: Infrastructure and Database Teams
**Review Frequency**: Quarterly
