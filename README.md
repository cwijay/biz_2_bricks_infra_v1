# biz2bricks-infra

Infrastructure provisioning CLI for Biz2Bricks. Provisions GCP resources using gcloud/gsutil commands.

## What Gets Created

| Resource | Description |
|----------|-------------|
| **Cloud SQL** | PostgreSQL 15 instance (db-f1-micro, 10GB SSD, us-central1) |
| **GCS Bucket** | Storage bucket with versioning and uniform access enabled |
| **Service Account** | `document-intelligence-api-sa` with Cloud SQL, Storage, and Secret Manager roles |
| **Secrets** | DATABASE_PASSWORD, JWT_SECRET_KEY, REFRESH_SECRET_KEY in Secret Manager |

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

## Quick Start: Complete GCP Setup

### Step 1: Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Configure Environment

Create a `.env` file in the project root with your configuration:

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

### Step 5: Initialize Database Schema

```bash
biz2bricks db init
```

This creates all database tables from the SQLAlchemy models.

### Step 6: Verify Resources

```bash
# Check Cloud SQL
gcloud sql instances describe YOUR_INSTANCE_NAME --format="table(name,state,region)"

# Check GCS bucket
gsutil ls -b gs://YOUR_BUCKET_NAME

# Check service account
gcloud iam service-accounts list --filter="email:document-intelligence"

# Check secrets
gcloud secrets list
```

Or view in GCP Console:
- **Cloud SQL**: https://console.cloud.google.com/sql/instances
- **Storage**: https://console.cloud.google.com/storage/browser
- **IAM**: https://console.cloud.google.com/iam-admin/serviceaccounts
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager

## CLI Reference

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

### Migration Commands

```bash
biz2bricks migrate upgrade head    # Apply all pending migrations
biz2bricks migrate downgrade -1    # Rollback one migration
biz2bricks migrate current         # Show current migration revision
biz2bricks migrate history         # Show migration history
```

### Other Commands

```bash
biz2bricks generate-env --project-id PROJECT_ID  # Generate .env from provisioned resources
```

## Force Recreating Resources

The provisioning commands are **idempotent** - they skip existing resources. The `--force` flag only skips confirmation prompts, it does NOT force recreate resources.

To force recreate all resources from scratch:

```bash
# Step 1: Delete all existing resources
biz2bricks delete all --force

# Step 2: Provision fresh resources
biz2bricks provision full-setup --force

# Step 3: Recreate database schema
biz2bricks db init
```

To recreate individual resources:

```bash
# Example: Recreate only Cloud SQL
biz2bricks delete cloud-sql --force
biz2bricks provision cloud-sql --force
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

Use delete commands first, then provision:

```bash
biz2bricks delete all --force
biz2bricks provision full-setup --force
```
