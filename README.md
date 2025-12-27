# biz2bricks-infra

Infrastructure provisioning CLI for Biz2Bricks. Provisions GCP resources using gcloud/gsutil commands.

## What Gets Created

| Resource | Description |
|----------|-------------|
| **Cloud SQL** | PostgreSQL 15 instance (db-f1-micro, 10GB SSD, us-central1) |
| **GCS Bucket** | Storage bucket with versioning and uniform access enabled |
| **Service Account** | `document-intelligence-api-sa` with Cloud SQL, Storage, and Secret Manager roles |
| **Secrets** | DATABASE_PASSWORD, JWT_SECRET_KEY, REFRESH_SECRET_KEY in Secret Manager |

## Database Tables

All database tables are defined in **biz2bricks_core** and created by the `biz2bricks setup all` command:

| Category | Tables | Description |
|----------|--------|-------------|
| **Core** | organizations, users, folders, documents, audit_logs | Multi-tenant organization and document management |
| **AI Processing** | processing_jobs, document_generations | Job tracking and generated content cache |
| **Memory** | user_preferences, conversation_summaries, memory_entries | Long-term memory for AI agents |
| **RAG** | file_search_stores, document_folders | Gemini File Search store registry |
| **Usage Tracking** | subscription_tiers, organization_subscriptions, token_usage_records, resource_usage_records, usage_aggregations | Quota management and usage analytics |
| **Semantic Cache** | rag_query_cache | RAG query caching with pgvector (768-dim embeddings) |

**Total: 18 tables** created from SQLAlchemy models.

## Prerequisites

1. **Python 3.12+**

2. **Google Cloud SDK** - Install from https://cloud.google.com/sdk/docs/install
   ```bash
   gcloud --version
   gsutil --version
   ```

3. **GCP Project** with billing enabled

4. **Required APIs** - Enable these in your GCP project:
   ```bash
   gcloud services enable \
     sqladmin.googleapis.com \
     storage.googleapis.com \
     iam.googleapis.com \
     secretmanager.googleapis.com
   ```

## Installation

### Step 1: Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Package

```bash
# Install the package (biz2bricks-core is fetched from GitHub automatically)
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Troubleshooting Installation

If you get `ModuleNotFoundError: No module named 'biz2bricks_infra'`:

```bash
# Uninstall and reinstall
pip uninstall biz2bricks-infra -y
pip cache purge
pip install -e .
```

If that still fails, recreate the virtual environment:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start: One-Command Setup

The fastest way to set up a complete environment:

### Step 1: Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Create Configuration File

Create a `.env.production` file with minimal required settings:

```env
GCP_PROJECT_ID=your-project-id
CLOUD_SQL_INSTANCE=your-project-id:us-central1:doc-intelligence-db
DATABASE_NAME=doc_intelligence
DATABASE_USER=postgres
DATABASE_PASSWORD=  # Will be auto-generated
GCS_BUCKET_NAME=your-bucket-name
```

### Step 3: Run Complete Setup

```bash
# One command does everything!
biz2bricks setup all --project-id YOUR_PROJECT_ID

# Or preview first
biz2bricks setup all --project-id YOUR_PROJECT_ID --dry-run
```

This single command:
1. Checks prerequisites (gcloud auth, APIs)
2. Provisions GCP resources (Cloud SQL, GCS, Service Account, Secrets)
3. Generates `.env` file with connection details
4. Creates all database tables (including pgvector support)
5. Seeds subscription tiers (Free, Pro, Enterprise)
6. Validates the setup

### Step 4: Verify Resources Created

```bash
# Check status of all GCP resources
biz2bricks status --env-file .env
```

Expected output:
```
=== GCP Resource Status ===

--- Cloud SQL ---
  Instance: doc-intelligence-db - RUNNABLE
    Region: us-central1, Tier: db-f1-micro
    IP: x.x.x.x

--- GCS Bucket ---
  Bucket: your-project-document-store - EXISTS
    Versioning: Enabled

--- Service Account ---
  Service Account: document-intelligence-api-sa - EXISTS
    Email: document-intelligence-api-sa@your-project.iam.gserviceaccount.com
    Roles:
      - roles/cloudsql.client
      - roles/secretmanager.secretAccessor
      - roles/storage.objectAdmin

--- Secret Manager ---
  DATABASE_PASSWORD - EXISTS
  JWT_SECRET_KEY - EXISTS
  REFRESH_SECRET_KEY - EXISTS
```

### Step 5: Start Your Application

```bash
cd ../doc_intelligence_ai_v3.0
uvicorn src.main:app --reload
```

---

## Force Recreate: Delete and Recreate All Resources

To completely delete existing GCP resources and recreate them from scratch:

```bash
# Delete and recreate all resources (requires confirmation)
biz2bricks setup all --project-id YOUR_PROJECT_ID --force
```

This will:
1. **Prompt for confirmation** - Type 'DELETE' to confirm
2. Delete all existing resources:
   - Secret Manager secrets
   - Service Account and IAM bindings
   - GCS Bucket and all contents
   - Cloud SQL instance and all data
3. Provision fresh resources
4. Generate new `.env` file
5. Create database tables with pgvector support
6. Seed subscription tiers
7. Validate the setup

**Preview force recreate (without executing):**
```bash
biz2bricks setup all --project-id YOUR_PROJECT_ID --force --dry-run
```

---

## Alternative: Step-by-Step Setup

If you prefer more control, use the individual commands:

### Step 1: Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Configure Environment

Create a `.env.production` file in the project root:

```env
# =============================================================================
# GCP Configuration
# =============================================================================
GCP_PROJECT_ID=your-project-id

# =============================================================================
# Cloud SQL Configuration
# =============================================================================
# IMPORTANT: Use format "project:region:instance"
CLOUD_SQL_INSTANCE=your-project-id:us-central1:your-instance-name

# Database credentials
DATABASE_NAME=doc_intelligence
DATABASE_USER=postgres
DATABASE_PASSWORD=your-secure-password

# REQUIRED: Enable Cloud SQL Python Connector for remote connections
USE_CLOUD_SQL_CONNECTOR=true

# =============================================================================
# Cloud Storage
# =============================================================================
GCS_BUCKET_NAME=your-bucket-name

# =============================================================================
# Authentication Secrets (auto-generated if empty during provisioning)
# =============================================================================
JWT_SECRET_KEY=
REFRESH_SECRET_KEY=
```

**Important:** The `USE_CLOUD_SQL_CONNECTOR=true` setting is required for connecting to Cloud SQL from your local machine.

### Step 3: Preview Changes (Optional)

```bash
biz2bricks provision full-setup --dry-run
```

### Step 4: Provision GCP Resources

```bash
biz2bricks provision full-setup --force
```

This creates:
- Cloud SQL PostgreSQL instance
- Database and user
- GCS bucket with versioning
- Service account with IAM roles
- Secrets in Secret Manager

### Step 5: Generate Environment File

```bash
biz2bricks generate-env --project-id YOUR_PROJECT_ID -o .env
```

### Step 6: Initialize Database Schema

```bash
biz2bricks db init --env-file .env
```

This creates all database tables from the SQLAlchemy models.

### Step 7: Seed Subscription Tiers

```bash
biz2bricks seed tiers --env-file .env
```

This creates the default Free, Pro, and Enterprise subscription tiers.

### Step 8: Verify Resources

```bash
# Quick status check (recommended)
biz2bricks status --env-file .env

# Or use gcloud commands directly:
gcloud sql instances describe YOUR_INSTANCE_NAME --format="table(name,state,region)"
gsutil ls -b gs://YOUR_BUCKET_NAME
gcloud iam service-accounts list --filter="email:document-intelligence"
gcloud secrets list
```

Or view in GCP Console:
- **Cloud SQL**: https://console.cloud.google.com/sql/instances
- **Storage**: https://console.cloud.google.com/storage/browser
- **IAM**: https://console.cloud.google.com/iam-admin/serviceaccounts
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager

## CLI Reference

### Setup Commands (Recommended)

```bash
# Complete one-command setup
biz2bricks setup all --project-id PROJECT_ID [OPTIONS]

Options:
  --project-id TEXT     GCP project ID (required)
  --region TEXT         GCP region (default: us-central1)
  --env-file PATH       Provisioning config file (default: .env.production)
  --output-env PATH     Output .env file for app (default: .env)
  --dry-run             Preview actions without executing
  --force               DELETE existing resources first, then recreate (destructive!)
  --skip-gcp            Skip GCP resource provisioning
  --skip-db             Skip database table creation
  --skip-seed           Skip subscription tier seeding
  --skip-validation     Skip final validation

# Database-only setup (when GCP resources already exist)
biz2bricks setup db-only --env-file .env
```

**Examples:**
```bash
# Full setup for new environment
biz2bricks setup all --project-id my-project

# Preview what would be done
biz2bricks setup all --project-id my-project --dry-run

# Force delete and recreate all resources
biz2bricks setup all --project-id my-project --force

# Skip GCP (resources already exist), just setup database
biz2bricks setup all --project-id my-project --skip-gcp

# Only create database tables
biz2bricks setup db-only --env-file .env
```

### Status Command

```bash
# Check status of all GCP resources
biz2bricks status --env-file .env
```

Shows:
- Cloud SQL instance state and IP
- GCS bucket existence and versioning
- Service account and IAM roles
- Secret Manager secrets

### Provision Commands

```bash
biz2bricks provision full-setup [OPTIONS]       # All resources
biz2bricks provision cloud-sql [OPTIONS]        # Only Cloud SQL
biz2bricks provision gcs-bucket [OPTIONS]       # Only GCS bucket
biz2bricks provision service-account [OPTIONS]  # Only service account
biz2bricks provision secrets [OPTIONS]          # Only secrets

Options:
  --env-file PATH   Environment file (default: .env.production)
  --dry-run         Preview without executing
  --force           Skip confirmation prompts (does NOT force recreate)
```

### Delete Commands

```bash
biz2bricks delete all --force              # Delete ALL resources
biz2bricks delete cloud-sql --force        # Delete Cloud SQL instance
biz2bricks delete gcs-bucket --force       # Delete GCS bucket and contents
biz2bricks delete service-account --force  # Delete service account
biz2bricks delete secrets --force          # Delete all secrets
```

### Database Commands

```bash
biz2bricks db init [--env-file .env]           # Create tables from SQLAlchemy models
biz2bricks db status [--env-file .env]         # Show database status and tables
biz2bricks db reset [--env-file .env] [--force] # Drop ALL tables and recreate schema
```

**WARNING:** `db reset` is destructive - it drops all tables and data!

The `db reset` command:
1. Drops all tables (CASCADE)
2. Enables pgvector extension
3. Recreates all tables with proper Vector(768) columns
4. Ready for vector index creation

### Seed Commands

```bash
biz2bricks seed tiers [OPTIONS]            # Seed subscription tiers (Free/Pro/Enterprise)

Options:
  --env-file PATH   Environment file (default: .env)
  --list, -l        List current tiers without seeding
  --reset, -r       Delete all tiers and re-seed
  --force, -f       Skip confirmation prompts
```

**Default Tiers:**
| Tier | Tokens/mo | Pages | Queries | Storage | Price |
|------|-----------|-------|---------|---------|-------|
| Free | 50,000 | 50 | 100 | 1 GB | $0/mo |
| Pro | 500,000 | 500 | 1,000 | 10 GB | $29/mo |
| Enterprise | 5,000,000 | 5,000 | 10,000 | 100 GB | $199/mo |

### Migration Commands

```bash
biz2bricks migrate upgrade head    # Apply all pending migrations
biz2bricks migrate downgrade -1    # Rollback one migration
biz2bricks migrate current         # Show current migration revision
biz2bricks migrate history         # Show migration history
```

### Utility Commands

```bash
biz2bricks generate-env --project-id PROJECT_ID  # Generate .env from provisioned resources
biz2bricks status --env-file .env                # Show status of all provisioned resources
biz2bricks sa create-key -o key.json             # Create service account JSON key
biz2bricks secrets get SECRET_NAME               # Get secret value from Secret Manager
biz2bricks secrets list                          # List all secrets
```

## Common Workflows

### New Environment Setup
```bash
biz2bricks setup all --project-id my-project
biz2bricks status --env-file .env
```

### Force Recreate Everything
```bash
biz2bricks setup all --project-id my-project --force
# Type 'DELETE' when prompted
biz2bricks status --env-file .env
```

### Reset Database Only (Keep GCP Resources)
```bash
biz2bricks db reset --force --env-file .env
biz2bricks seed tiers --env-file .env
```

### Skip GCP, Just Database Setup
```bash
biz2bricks setup all --project-id my-project --skip-gcp --env-file .env
```

## Updating biz2bricks-core

To update to the latest version of biz2bricks-core from GitHub:

```bash
pip install -e . --force-reinstall --no-cache-dir
```

## Environment File Notes

- **`.env`** - Used by `biz2bricks-core` for database connections (loaded at import time)
- **`.env.production`** - Used by provisioning commands (can be specified with `--env-file`)

For database commands (`db init`, `db status`), ensure your `.env` file has the correct settings including `USE_CLOUD_SQL_CONNECTOR=true`.

## Architecture

### Project Structure

```
src/biz2bricks_infra/
├── cli.py                 # Click-based CLI entry point
├── commands/
│   ├── setup.py           # Complete setup orchestration (setup all command)
│   └── seed.py            # Subscription tier seeding
├── provision/
│   ├── config.py          # ProvisioningConfig dataclass
│   ├── provisioner.py     # GCP resource provisioning via gcloud
│   └── env_generator.py   # .env file generation
└── gcloud/
    └── commands.py        # gcloud/gsutil command wrappers
```

### Consolidated Models

All SQLAlchemy models are defined in **biz2bricks_core**:

```
biz2bricks_core/src/biz2bricks_core/models/
├── base.py       # Base class, enums (AuditAction, AuditEntityType)
├── core.py       # OrganizationModel, UserModel, FolderModel
├── documents.py  # DocumentModel, AuditLogModel
├── usage.py      # SubscriptionTierModel, OrganizationSubscriptionModel, TokenUsageRecordModel
└── rag.py        # RAGQueryCacheModel (with pgvector Vector(768) column)
```

### Table Creation Options

You have **two equivalent ways** to create database tables:

**Option 1: Using biz2bricks_infra (recommended)**
```bash
biz2bricks setup all --project-id PROJECT_ID
# Or just database setup:
biz2bricks setup db-only --env-file .env
```

**Option 2: Using doc_intelligence_ai_v3.0 scripts**
```bash
cd ../doc_intelligence_ai_v3.0
python scripts/db_setup.py setup      # Create all tables
python scripts/db_setup.py status     # Check database state
python scripts/db_setup.py reset      # Drop and recreate all tables
```

Both methods import models from biz2bricks_core, so they create **identical schemas**.

## Troubleshooting

### "gcloud not authenticated"

```bash
gcloud auth login
gcloud auth application-default login
```

### "API not enabled"

```bash
gcloud services enable sqladmin.googleapis.com storage.googleapis.com iam.googleapis.com secretmanager.googleapis.com
```

### "Permission denied"

Ensure your account has these roles:
- `roles/cloudsql.admin`
- `roles/storage.admin`
- `roles/iam.serviceAccountAdmin`
- `roles/secretmanager.admin`

### Database connection fails (localhost:5432)

This means `USE_CLOUD_SQL_CONNECTOR=true` is missing from your `.env` file. Add it:

```bash
echo "USE_CLOUD_SQL_CONNECTOR=true" >> .env
```

### "ModuleNotFoundError: No module named 'biz2bricks_infra'"

Reinstall the package:

```bash
pip uninstall biz2bricks-infra -y
pip install -e .
```

If that doesn't work, recreate the virtual environment (see Installation section).

### Resources "already exist" but you want to recreate

Use the `--force` flag with `setup all`:

```bash
biz2bricks setup all --project-id my-project --force
```

Or manually delete and reprovision:

```bash
biz2bricks delete all --force
biz2bricks provision full-setup --force
```

### pgvector extension not available

Cloud SQL supports pgvector. Ensure the extension is enabled:

```bash
biz2bricks db reset --force --env-file .env
```

This will drop all tables, enable pgvector extension, and recreate tables with proper Vector columns.
