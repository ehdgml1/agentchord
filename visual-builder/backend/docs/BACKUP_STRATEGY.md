# Database Backup Strategy

## Overview

This document outlines the backup and recovery strategy for AgentWeave Visual Builder database (PostgreSQL in production, SQLite in development).

## Production Environment (PostgreSQL)

### Backup Schedule

| Type | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| Full Backup | Daily at 02:00 UTC | 7 daily | pg_dump |
| WAL Archive | Continuous | 24 hours | pg_basebackup + archive_command |
| Weekly Backup | Sunday 02:00 UTC | 4 weekly snapshots | pg_dump |
| Monthly Backup | 1st of month 02:00 UTC | 12 monthly snapshots | pg_dump |

### Implementation

#### 1. WAL Archiving (Continuous Backup)

Enable WAL archiving in PostgreSQL configuration (`postgresql.conf`):

```conf
wal_level = replica
archive_mode = on
archive_command = '/usr/local/bin/archive_wal.sh %p %f'
archive_timeout = 300  # 5 minutes
```

Archive script (`/usr/local/bin/archive_wal.sh`):

```bash
#!/bin/bash
# Archive WAL to S3/MinIO
WAL_PATH=$1
WAL_FILE=$2
BUCKET="agentweave-backups"
PREFIX="wal-archive/$(date +%Y-%m-%d)"

# Copy to S3/MinIO
aws s3 cp "$WAL_PATH" "s3://$BUCKET/$PREFIX/$WAL_FILE" \
  --endpoint-url="${MINIO_ENDPOINT}" \
  --region="${AWS_REGION:-us-east-1}"

# Verify upload
if [ $? -eq 0 ]; then
  exit 0
else
  echo "WAL archive failed: $WAL_FILE" >&2
  exit 1
fi
```

#### 2. Daily Full Backups (Cron)

Crontab entry:

```cron
# Daily full backup at 02:00 UTC
0 2 * * * /usr/local/bin/backup_postgres.sh daily

# Weekly backup on Sunday at 02:00 UTC
0 2 * * 0 /usr/local/bin/backup_postgres.sh weekly

# Monthly backup on 1st at 02:00 UTC
0 2 1 * * /usr/local/bin/backup_postgres.sh monthly
```

Backup script (`/usr/local/bin/backup_postgres.sh`):

```bash
#!/bin/bash
set -euo pipefail

BACKUP_TYPE=${1:-daily}  # daily, weekly, monthly
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUCKET="agentweave-backups"
DB_NAME="${DATABASE_NAME:-agentweave}"
DB_USER="${DATABASE_USER:-postgres}"
DB_HOST="${DATABASE_HOST:-localhost}"

BACKUP_FILE="backup_${BACKUP_TYPE}_${TIMESTAMP}.sql.gz"
LOCAL_PATH="/tmp/${BACKUP_FILE}"

# Create compressed dump
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom --compress=9 --verbose \
  --file="$LOCAL_PATH"

# Upload to S3/MinIO
aws s3 cp "$LOCAL_PATH" "s3://$BUCKET/dumps/$BACKUP_TYPE/$BACKUP_FILE" \
  --endpoint-url="${MINIO_ENDPOINT}" \
  --storage-class STANDARD_IA

# Cleanup local file
rm -f "$LOCAL_PATH"

# Retention cleanup
case "$BACKUP_TYPE" in
  daily)
    # Keep 7 daily backups
    aws s3 ls "s3://$BUCKET/dumps/daily/" --endpoint-url="${MINIO_ENDPOINT}" \
      | sort -r | tail -n +8 | awk '{print $4}' \
      | xargs -I {} aws s3 rm "s3://$BUCKET/dumps/daily/{}" --endpoint-url="${MINIO_ENDPOINT}"
    ;;
  weekly)
    # Keep 4 weekly backups
    aws s3 ls "s3://$BUCKET/dumps/weekly/" --endpoint-url="${MINIO_ENDPOINT}" \
      | sort -r | tail -n +5 | awk '{print $4}' \
      | xargs -I {} aws s3 rm "s3://$BUCKET/dumps/weekly/{}" --endpoint-url="${MINIO_ENDPOINT}"
    ;;
  monthly)
    # Keep 12 monthly backups
    aws s3 ls "s3://$BUCKET/dumps/monthly/" --endpoint-url="${MINIO_ENDPOINT}" \
      | sort -r | tail -n +13 | awk '{print $4}' \
      | xargs -I {} aws s3 rm "s3://$BUCKET/dumps/monthly/{}" --endpoint-url="${MINIO_ENDPOINT}"
    ;;
esac

echo "Backup completed: $BACKUP_FILE"
```

#### 3. Storage Configuration

**S3/MinIO Bucket Structure:**

```
agentweave-backups/
├── dumps/
│   ├── daily/       # 7 days retention
│   ├── weekly/      # 4 weeks retention
│   └── monthly/     # 12 months retention
└── wal-archive/
    └── YYYY-MM-DD/  # 24 hours retention
```

**Lifecycle Policy (S3/MinIO):**

```json
{
  "Rules": [
    {
      "Id": "ExpireWALAfter1Day",
      "Status": "Enabled",
      "Prefix": "wal-archive/",
      "Expiration": {
        "Days": 1
      }
    }
  ]
}
```

### Restore Procedure

#### Point-in-Time Recovery (PITR)

1. Stop PostgreSQL service:
   ```bash
   systemctl stop postgresql
   ```

2. Remove current data directory:
   ```bash
   mv /var/lib/postgresql/data /var/lib/postgresql/data.old
   mkdir /var/lib/postgresql/data
   chown postgres:postgres /var/lib/postgresql/data
   ```

3. Restore base backup:
   ```bash
   # Download and extract latest base backup
   LATEST_BACKUP=$(aws s3 ls s3://agentweave-backups/dumps/daily/ \
     --endpoint-url="${MINIO_ENDPOINT}" | sort -r | head -n 1 | awk '{print $4}')

   aws s3 cp "s3://agentweave-backups/dumps/daily/$LATEST_BACKUP" /tmp/backup.sql.gz \
     --endpoint-url="${MINIO_ENDPOINT}"

   # Restore using pg_restore
   createdb -h localhost -U postgres agentweave
   pg_restore -h localhost -U postgres -d agentweave -v /tmp/backup.sql.gz
   ```

4. Restore WAL archives (for PITR):
   ```bash
   # Download WAL files for specific timeframe
   TARGET_DATE="2026-02-15"
   aws s3 sync "s3://agentweave-backups/wal-archive/$TARGET_DATE/" \
     /var/lib/postgresql/data/pg_wal/ \
     --endpoint-url="${MINIO_ENDPOINT}"
   ```

5. Create recovery configuration (`recovery.conf` or `postgresql.auto.conf`):
   ```conf
   restore_command = 'aws s3 cp s3://agentweave-backups/wal-archive/%f %p --endpoint-url=${MINIO_ENDPOINT}'
   recovery_target_time = '2026-02-15 14:30:00 UTC'  # Optional: specific time
   ```

6. Start PostgreSQL and verify:
   ```bash
   systemctl start postgresql
   psql -U postgres -d agentweave -c "SELECT COUNT(*) FROM workflows;"
   ```

#### Full Backup Restore (Simpler, No PITR)

```bash
# Download specific backup
aws s3 cp s3://agentweave-backups/dumps/daily/backup_daily_20260215_020000.sql.gz /tmp/restore.sql.gz \
  --endpoint-url="${MINIO_ENDPOINT}"

# Drop and recreate database
dropdb -h localhost -U postgres agentweave
createdb -h localhost -U postgres agentweave

# Restore
pg_restore -h localhost -U postgres -d agentweave -v /tmp/restore.sql.gz
```

### Verification & Testing

#### Monthly Backup Verification (Automated)

Crontab entry:

```cron
# Test restore on 2nd of each month at 03:00 UTC
0 3 2 * * /usr/local/bin/test_restore.sh
```

Test script (`/usr/local/bin/test_restore.sh`):

```bash
#!/bin/bash
set -euo pipefail

BUCKET="agentweave-backups"
TEST_DB="agentweave_restore_test"

# Get latest monthly backup
LATEST_BACKUP=$(aws s3 ls s3://$BUCKET/dumps/monthly/ \
  --endpoint-url="${MINIO_ENDPOINT}" | sort -r | head -n 1 | awk '{print $4}')

# Download backup
aws s3 cp "s3://$BUCKET/dumps/monthly/$LATEST_BACKUP" /tmp/test_restore.sql.gz \
  --endpoint-url="${MINIO_ENDPOINT}"

# Drop test DB if exists, create new
dropdb -h localhost -U postgres --if-exists "$TEST_DB"
createdb -h localhost -U postgres "$TEST_DB"

# Restore
pg_restore -h localhost -U postgres -d "$TEST_DB" -v /tmp/test_restore.sql.gz

# Verify core tables exist
TABLES=$(psql -h localhost -U postgres -d "$TEST_DB" -t -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

if [ "$TABLES" -lt 10 ]; then
  echo "ERROR: Restore test failed - insufficient tables ($TABLES)" >&2
  exit 1
fi

# Cleanup
dropdb -h localhost -U postgres "$TEST_DB"
rm -f /tmp/test_restore.sql.gz

echo "Restore test PASSED: $LATEST_BACKUP restored successfully with $TABLES tables"
```

#### Manual Verification Checklist

- [ ] Verify backup file exists in S3/MinIO bucket
- [ ] Check backup file size (should be >1MB for production DB)
- [ ] Test restore to temporary database
- [ ] Verify row counts in critical tables (workflows, executions, users)
- [ ] Check data integrity (foreign keys, constraints)
- [ ] Validate latest timestamp in restored data

## Development Environment (SQLite)

### Backup Strategy

SQLite backups are simpler:

```bash
# Daily backup
cp tool_hub.db backups/tool_hub_$(date +%Y%m%d).db

# Retention: keep last 7 days
find backups/ -name "tool_hub_*.db" -mtime +7 -delete
```

### Restore Procedure

```bash
# Stop application
systemctl stop agentweave

# Restore from specific backup
cp backups/tool_hub_20260215.db tool_hub.db

# Restart application
systemctl start agentweave
```

## Disaster Recovery RTO/RPO

| Scenario | RTO (Recovery Time) | RPO (Data Loss) |
|----------|---------------------|-----------------|
| Full DB Restore (latest daily backup) | 15 minutes | Up to 24 hours |
| Point-in-Time Recovery (PITR with WAL) | 30 minutes | Up to 5 minutes |
| Corruption Recovery (weekly backup) | 20 minutes | Up to 7 days |

## Monitoring & Alerts

Set up monitoring for:

- Backup job failures (email/Slack alerts)
- Backup file size anomalies (too small = incomplete backup)
- S3/MinIO bucket availability
- WAL archive lag (should be <5 minutes)
- Backup storage usage (alert if >80% quota)

Example monitoring with cron + healthcheck:

```bash
# Add to cron
*/15 * * * * /usr/local/bin/check_backup_health.sh
```

Healthcheck script:

```bash
#!/bin/bash
LATEST_BACKUP_AGE=$(aws s3 ls s3://agentweave-backups/dumps/daily/ \
  --endpoint-url="${MINIO_ENDPOINT}" | sort -r | head -n 1 \
  | awk '{print $1" "$2}' | xargs -I {} date -d "{}" +%s)

NOW=$(date +%s)
AGE_HOURS=$(( (NOW - LATEST_BACKUP_AGE) / 3600 ))

if [ $AGE_HOURS -gt 26 ]; then
  echo "ALERT: Latest backup is $AGE_HOURS hours old (threshold: 26h)" >&2
  # Send alert via your monitoring system
  exit 1
fi
```

## Security Considerations

1. Encrypt backups at rest (S3 SSE-KMS or MinIO encryption)
2. Encrypt backups in transit (TLS for S3/MinIO)
3. Restrict bucket access (IAM policies, least privilege)
4. Store backup credentials in secrets manager (not in cron)
5. Audit backup access logs regularly

## References

- [PostgreSQL WAL Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [AWS S3 Lifecycle Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
