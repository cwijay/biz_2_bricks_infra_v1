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
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable iam.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

## Installation

**Prerequisite:** SSH key must be configured for GitHub access (the core dependency is a private repo).
```bash
ssh -T git@github.com   # Verify SSH authentication works
```

```bash
# Install the package (biz2bricks-core is fetched from GitHub automatically)
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Creating a Fresh GCP Environment

### Step 1: Authenticate with GCP

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify
gcloud config get-value project
```

### Step 2: Enable Required APIs

```bash
gcloud services enable \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  secretmanager.googleapis.com
```

### Step 3: Configure Environment

Edit `.env.production` with your values:

```env
# Required
GCP_PROJECT_ID=your-project-id

# Cloud SQL (instance name only, not full path)
CLOUD_SQL_INSTANCE=your-instance-name
DATABASE_NAME=doc_intelligence
DATABASE_USER=postgres
DATABASE_PASSWORD=your-secure-password

# GCS
GCS_BUCKET_NAME=your-bucket-name

# Auth secrets (leave empty to auto-generate)
JWT_SECRET_KEY=
REFRESH_SECRET_KEY=
```

### Step 4: Preview Changes (Dry Run)

```bash
biz2bricks provision full-setup --dry-run
```

This shows what will be created without making changes.

### Step 5: Provision Resources

```bash
biz2bricks provision full-setup
```

You'll be prompted to confirm. Use `--force` to skip confirmation.

### Step 6: Verify in GCP Console

- **Cloud SQL**: https://console.cloud.google.com/sql/instances
- **Storage**: https://console.cloud.google.com/storage/browser
- **IAM**: https://console.cloud.google.com/iam-admin/serviceaccounts
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager

### Step 7: Run Database Migrations

```bash
biz2bricks migrate upgrade head
```

## CLI Reference

### Provision Commands

```bash
biz2bricks provision full-setup [OPTIONS]    # All resources
biz2bricks provision cloud-sql [OPTIONS]     # Only Cloud SQL
biz2bricks provision gcs-bucket [OPTIONS]    # Only GCS bucket
biz2bricks provision service-account [OPTIONS]  # Only service account
biz2bricks provision secrets [OPTIONS]       # Only secrets

Options:
  --env-file PATH   Environment file (default: .env.production)
  --dry-run         Preview without executing
  --force           Skip confirmation prompts
```

### Migration Commands

```bash
biz2bricks migrate upgrade [REVISION]   # Upgrade to revision (default: head)
biz2bricks migrate downgrade [REVISION] # Downgrade (default: -1)
biz2bricks migrate current              # Show current revision
biz2bricks migrate history [-v]         # Show migration history
biz2bricks migrate revision -m "msg"    # Create new migration
```

### Environment Generation

```bash
biz2bricks generate-env --project-id PROJECT_ID [-o OUTPUT_FILE]
```

Discovers provisioned resources and generates a `.env` file.

## Troubleshooting

### "gcloud not authenticated"
```bash
gcloud auth login
gcloud auth application-default login
```

### "API not enabled"
```bash
gcloud services enable sqladmin.googleapis.com
# ... enable other required APIs
```

### "Permission denied"
Ensure your account has these roles:
- `roles/cloudsql.admin`
- `roles/storage.admin`
- `roles/iam.serviceAccountAdmin`
- `roles/secretmanager.admin`

### "biz2bricks-core not found"
Install the core package first:
```bash
pip install -e ../biz2bricks_core
```

## Provisioning Individual Resources

You can provision resources separately:

```bash
# Create only the Cloud SQL instance
biz2bricks provision cloud-sql

# Create only the GCS bucket
biz2bricks provision gcs-bucket

# Create only the service account
biz2bricks provision service-account

# Create only the secrets
biz2bricks provision secrets
```

Each command is idempotent - it checks if the resource exists before creating.
