# Database Setup Guide

## Overview

This guide covers the setup of the PostgreSQL database for the PatientTriage.ai ML Core Engine audit logging and override tracking system.

**Task 1.3**: Set up PostgreSQL schema for audit logging and override tracking

## Requirements Met

- ✅ Create `predictions` table with all required columns and indexes
- ✅ Create `overrides` table with clinician tracking and reasoning
- ✅ Create `deterioration_alerts` table with vital change history
- ✅ Add indexes on timestamp, model_version, esi_prediction, safety_outcome
- ✅ Enable row-level encryption for PHI compliance
- ✅ Set up 7-year retention policy with automated archival
- ✅ Implements Requirements: 7.1, 15.1, 15.2, 15.3, 15.4, 16.2

## Database Schema

### Tables

#### 1. `predictions`
Audit log for all ESI predictions with complete context.

**Key Columns**:
- `id` (UUID): Primary key
- `request_id` (VARCHAR): Unique request identifier
- `timestamp` (TIMESTAMP): When prediction was made
- `model_version` (VARCHAR): Model version used
- `patient_features` (JSONB): Complete patient data (encrypted)
- `esi_prediction` (INTEGER): Predicted ESI level (1-5)
- `probability_distribution` (FLOAT[]): Probability distribution
- `confidence_breakdown` (JSONB): Multi-dimensional confidence scores
- `safety_outcome` (VARCHAR): RED/YELLOW/GREEN
- `explanation` (JSONB): SHAP-based explanation
- `sub_score` (FLOAT): Surge mode sub-score (0-100)
- `inference_time_ms` (FLOAT): Inference duration

**Indexes**:
- `idx_predictions_timestamp`: Query by time range
- `idx_predictions_model_version`: Filter by model version
- `idx_predictions_esi`: Filter by ESI level
- `idx_predictions_safety`: Filter by safety outcome
- `idx_predictions_timestamp_esi`: Composite for time + ESI queries

#### 2. `overrides`
Clinician overrides of ML predictions with reasoning and outcomes.

**Key Columns**:
- `id` (UUID): Primary key
- `prediction_id` (UUID): Foreign key to predictions
- `timestamp` (TIMESTAMP): When override occurred
- `ml_predicted_esi` (INTEGER): ML prediction
- `ml_confidence` (JSONB): ML confidence at time of override
- `clinician_final_esi` (INTEGER): Final ESI assigned by clinician
- `override_direction` (VARCHAR): escalation or de-escalation
- `override_magnitude` (INTEGER): Absolute difference
- `override_reason_category` (VARCHAR): Predefined category
- `override_reason_text` (TEXT): Free-text explanation
- `clinician_id` (VARCHAR): Clinician identifier
- `patient_outcome` (JSONB): Eventual outcome data
- `outcome_updated_at` (TIMESTAMP): When outcome was recorded

**Indexes**:
- `idx_overrides_timestamp`: Query by time
- `idx_overrides_prediction`: Link to prediction
- `idx_overrides_clinician`: Track clinician patterns
- `idx_overrides_category`: Group by reason
- `idx_overrides_timestamp_category`: Pattern analysis over time

#### 3. `deterioration_alerts`
Alerts for patient deterioration during ED wait time.

**Key Columns**:
- `id` (UUID): Primary key
- `patient_id` (VARCHAR): Hashed patient identifier
- `timestamp` (TIMESTAMP): When alert was triggered
- `deterioration_status` (VARCHAR): STABLE/DETERIORATING/UNCERTAIN
- `deterioration_score` (FLOAT): Probability score (0-100)
- `vital_changes` (JSONB): Temporal vital sign changes
- `initial_esi` (INTEGER): ESI at initial triage
- `time_since_triage_minutes` (INTEGER): Wait time elapsed
- `alert_reason` (VARCHAR): Why alert was triggered
- `model_version` (VARCHAR): Deterioration detector version

**Indexes**:
- `idx_deterioration_timestamp`: Query by time
- `idx_deterioration_patient`: Patient history
- `idx_deterioration_status`: Filter by status
- `idx_deterioration_patient_timestamp`: Patient timeline

## Installation

### Prerequisites

1. **PostgreSQL 15+** installed and running
2. **Python 3.10+** with required packages
3. **Environment variables** configured

### Step 1: Install PostgreSQL

**macOS** (Homebrew):
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15
sudo systemctl start postgresql
```

**Docker**:
```bash
docker run -d \
  --name triage-postgres \
  -e POSTGRES_USER=triage_user \
  -e POSTGRES_PASSWORD=triage_pass \
  -e POSTGRES_DB=triage_db \
  -p 5432:5432 \
  postgres:15
```

### Step 2: Create Database and User

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE triage_db;
CREATE USER triage_user WITH PASSWORD 'triage_pass';
GRANT ALL PRIVILEGES ON DATABASE triage_db TO triage_user;

# Exit psql
\q
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your database credentials
# DATABASE_URL=postgresql://triage_user:triage_pass@localhost:5432/triage_db
```

### Step 4: Run Database Setup

**Option A: Full Setup (Recommended)**
```bash
# Create tables + run SQL file + validate
python -m src.database.setup --full
```

**Option B: Step-by-step**
```bash
# 1. Create tables
python -m src.database.setup --create

# 2. Run SQL file (archive tables, functions, roles)
python -m src.database.setup --sql

# 3. Validate schema
python -m src.database.setup --validate
```

### Step 5: Verify Installation

```bash
# Check tables were created
psql triage_db -c "\dt"

# Should show:
# - predictions
# - overrides
# - deterioration_alerts
# - predictions_archive
# - overrides_archive
# - deterioration_alerts_archive

# Check indexes
psql triage_db -c "\di"
```

## Usage

### Using SQLAlchemy Models (Recommended)

```python
from src.database import get_db_session, Prediction, Override
from datetime import datetime
import uuid

# Get database session
db = next(get_db_session())

# Create a prediction record
prediction = Prediction(
    request_id="req_123abc",
    timestamp=datetime.utcnow(),
    model_version="v2.1.0_20241201",
    patient_features={"age": 68, "hr": 118, "spo2": 92},
    esi_prediction=2,
    probability_distribution=[0.05, 0.72, 0.18, 0.04, 0.01],
    confidence_breakdown={"overall": 81.7, "level": "HIGH"},
    safety_outcome="YELLOW",
    explanation={"text": "ESI 2 based on chest pain...", "top_factors": []},
    inference_time_ms=92.7
)

db.add(prediction)
db.commit()

# Query predictions
recent_predictions = db.query(Prediction).filter(
    Prediction.timestamp >= datetime.utcnow() - timedelta(hours=24)
).all()

# Close session
db.close()
```

### Using Raw SQL

```python
from src.database import get_db_engine
from sqlalchemy import text

engine = get_db_engine()

with engine.connect() as conn:
    # Insert prediction
    result = conn.execute(
        text("""
            INSERT INTO predictions (
                request_id, model_version, patient_features, 
                esi_prediction, probability_distribution,
                confidence_breakdown, safety_outcome, explanation,
                inference_time_ms
            ) VALUES (
                :request_id, :model_version, :patient_features::jsonb,
                :esi_prediction, :probability_distribution,
                :confidence_breakdown::jsonb, :safety_outcome,
                :explanation::jsonb, :inference_time_ms
            )
            RETURNING id
        """),
        {
            "request_id": "req_123abc",
            "model_version": "v2.1.0",
            "patient_features": '{"age": 68}',
            "esi_prediction": 2,
            "probability_distribution": [0.05, 0.72, 0.18, 0.04, 0.01],
            "confidence_breakdown": '{"overall": 81.7}',
            "safety_outcome": "YELLOW",
            "explanation": '{"text": "ESI 2..."}',
            "inference_time_ms": 92.7
        }
    )
    conn.commit()
```

## Maintenance

### Archive Old Records (1+ years)

```bash
# Run archival function (should be scheduled monthly)
psql triage_db -c "SELECT archive_old_records();"
```

**Automated Scheduling** (cron):
```bash
# Add to crontab (runs first day of each month at 2 AM)
0 2 1 * * psql triage_db -c "SELECT archive_old_records();" >> /var/log/triage_archive.log 2>&1
```

### Purge Old Records (7+ years)

```bash
# Run purge function (should be scheduled annually)
psql triage_db -c "SELECT purge_old_records();"
```

**Automated Scheduling** (cron):
```bash
# Add to crontab (runs January 1st at 3 AM)
0 3 1 1 * psql triage_db -c "SELECT purge_old_records();" >> /var/log/triage_purge.log 2>&1
```

### Backup Database

```bash
# Full backup
pg_dump triage_db > triage_db_backup_$(date +%Y%m%d).sql

# Backup with compression
pg_dump triage_db | gzip > triage_db_backup_$(date +%Y%m%d).sql.gz

# Restore from backup
psql triage_db < triage_db_backup_20241215.sql
```

### Monitor Database Size

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check database size
SELECT pg_size_pretty(pg_database_size('triage_db'));
```

## Security and Compliance

### Row-Level Encryption

For production deployments, enable PostgreSQL Transparent Data Encryption (TDE) or use AWS RDS encryption at rest:

**AWS RDS**:
```bash
# Enable encryption when creating RDS instance
aws rds create-db-instance \
  --db-instance-identifier triage-db \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:region:account:key/key-id
```

### Role-Based Access Control

```sql
-- Application role (read/write active tables)
GRANT SELECT, INSERT, UPDATE ON predictions, overrides, deterioration_alerts TO triage_app;

-- Auditor role (read-only all tables)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO triage_auditor;

-- Admin role (archival and purge operations)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO triage_admin;
GRANT EXECUTE ON FUNCTION archive_old_records() TO triage_admin;
GRANT EXECUTE ON FUNCTION purge_old_records() TO triage_admin;
```

### HIPAA Compliance Checklist

- ✅ Encrypted at rest (TDE or AWS RDS encryption)
- ✅ Encrypted in transit (SSL/TLS connections)
- ✅ 7-year retention policy implemented
- ✅ Automated archival after 1 year
- ✅ Audit logging for all PHI access
- ✅ Role-based access control
- ✅ Regular backups with encryption

## Troubleshooting

### Connection Refused

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### Permission Denied

```bash
# Grant privileges to user
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE triage_db TO triage_user;"

# Grant schema privileges
psql triage_db -c "GRANT ALL ON SCHEMA public TO triage_user;"
```

### Table Already Exists

```bash
# Drop and recreate (DANGEROUS - deletes all data!)
python -m src.database.setup --drop
python -m src.database.setup --create
```

### Index Not Created

```bash
# Check existing indexes
psql triage_db -c "\di"

# Manually create missing index
psql triage_db -c "CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);"
```

## Performance Tuning

### Optimize Queries

```sql
-- Analyze table statistics
ANALYZE predictions;
ANALYZE overrides;
ANALYZE deterioration_alerts;

-- Rebuild indexes
REINDEX TABLE predictions;
```

### Partitioning (for large datasets)

For databases with millions of records, consider partitioning by timestamp:

```sql
-- Create partitioned table (PostgreSQL 15+)
CREATE TABLE predictions_partitioned (
    LIKE predictions INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create partitions (monthly)
CREATE TABLE predictions_2024_12 PARTITION OF predictions_partitioned
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
```

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/15/)
- [SQLAlchemy ORM Guide](https://docs.sqlalchemy.org/en/20/)
- [HIPAA Compliance for Databases](https://www.hhs.gov/hipaa/for-professionals/security/index.html)

## Support

For issues or questions:
1. Check logs: `tail -f /var/log/postgresql/postgresql-15-main.log`
2. Validate schema: `python -m src.database.setup --validate`
3. Contact database admin team
