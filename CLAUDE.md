# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is `biz2bricks-infra`, a Python CLI tool that provisions GCP infrastructure using gcloud/gsutil commands (not Terraform). It creates Cloud SQL PostgreSQL instances, GCS buckets, service accounts, and Secret Manager secrets. It also manages database schema creation and Alembic migrations.

## Commands

### Installation
```bash
ssh -T git@github.com               # Verify SSH auth (biz2bricks-core is private repo)
pip install -e .                    # Install (fetches biz2bricks-core from GitHub)
pip install -e ".[dev]"             # Include dev dependencies (pytest, black, ruff, mypy)
```

### CLI Usage
```bash
# Complete environment setup (recommended)
biz2bricks setup all --project-id PROJECT  # Full setup: GCP + DB + seed data
biz2bricks setup all --project-id PROJECT --dry-run  # Preview without executing
biz2bricks setup all --project-id PROJECT --force    # Delete existing resources first, then recreate
biz2bricks setup all --project-id PROJECT --skip-gcp # Skip GCP, just DB setup

# Verify resources are created correctly
biz2bricks status --env-file .env           # Check all GCP resources status

# Provision GCP resources (individual)
biz2bricks provision full-setup     # Provision all GCP resources
biz2bricks provision full-setup --dry-run  # Preview without executing
biz2bricks provision cloud-sql      # Only Cloud SQL
biz2bricks provision gcs-bucket     # Only GCS bucket
biz2bricks provision service-account # Only service account
biz2bricks provision secrets        # Only secrets

# Delete GCP resources
biz2bricks delete all --force       # Delete ALL resources
biz2bricks delete cloud-sql --force # Delete Cloud SQL instance
biz2bricks delete gcs-bucket --force # Delete GCS bucket

# Database management
biz2bricks db init                  # Create tables from SQLAlchemy models
biz2bricks db status                # Show database status and tables
biz2bricks db reset --force         # Drop ALL tables, enable pgvector, recreate schema

# Seed data
biz2bricks seed tiers               # Seed subscription tiers (Free, Pro, Enterprise)
biz2bricks seed tiers --list        # List current tiers

# Alembic migrations (via biz2bricks-core)
biz2bricks migrate upgrade head     # Apply all pending migrations
biz2bricks migrate downgrade -1     # Rollback one migration
biz2bricks migrate current          # Show current migration revision
biz2bricks migrate history          # Show migration history

# Utilities
biz2bricks generate-env --project-id PROJECT  # Generate .env from provisioned resources
biz2bricks sa create-key -o key.json          # Create service account JSON key
biz2bricks secrets list                        # List all secrets
```

### Common Workflows

```bash
# New environment setup
biz2bricks setup all --project-id my-project
biz2bricks status --env-file .env

# Force recreate everything (deletes and recreates all GCP resources)
biz2bricks setup all --project-id my-project --force
# Type 'DELETE' when prompted
biz2bricks status --env-file .env

# Reset database only (keep GCP resources)
biz2bricks db reset --force --env-file .env
biz2bricks seed tiers --env-file .env

# Skip GCP, just database setup
biz2bricks setup all --project-id my-project --skip-gcp --env-file .env
```

### Development
```bash
ruff check src/                     # Lint
black src/                          # Format
mypy src/                           # Type check
pytest                              # Run tests
```

## Architecture

```
src/biz2bricks_infra/
├── cli.py                 # Click-based CLI entry point
├── commands/
│   ├── setup.py           # Complete setup orchestration (setup all command)
│   └── seed.py            # Subscription tier seeding
├── provision/
│   ├── config.py          # ProvisioningConfig dataclass, loads from .env files
│   ├── provisioner.py     # Orchestrates resource creation via gcloud commands
│   └── env_generator.py   # Discovers provisioned resources, generates .env files
└── gcloud/
    └── commands.py        # Wrappers for gcloud/gsutil subprocess calls
```

**Key design:** The provisioner wraps gcloud/gsutil CLI commands rather than using GCP Python SDKs directly. This provides idempotency (checks if resources exist before creating) and dry-run support.

## Configuration

The CLI reads from `.env.production` by default (override with `--env-file`). Required variables:
- `GCP_PROJECT_ID` (required)
- `CLOUD_SQL_INSTANCE` (format: `project:region:instance`)
- `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`
- `GCS_BUCKET_NAME`
- `JWT_SECRET_KEY`, `REFRESH_SECRET_KEY` (auto-generated if empty)

## Dependencies

- `biz2bricks-core` - Private GitHub repo `git+ssh://git@github.com/cwijay/biz_to_bricks_core_v1.git` (database models, Alembic migrations)
- Google Cloud SDK (`gcloud`, `gsutil`) - Must be installed and authenticated

## Database Schema

The database includes 18 tables from biz2bricks_core, organized into modules:

**Core Tables:**
- `organizations` - Multi-tenant organization data
- `users` - User accounts (scoped by organization)
- `folders` - Document folder hierarchy
- `documents` - Document metadata and content
- `audit_logs` - Audit trail for all operations

**Usage/Billing Tables:**
- `subscription_tiers` - Subscription tier definitions (Free, Pro, Enterprise)
- `organization_subscriptions` - Organization subscription status
- `token_usage_records` - Token usage tracking
- `resource_usage_records` - Resource usage tracking
- `usage_aggregations` - Aggregated usage statistics

**AI Module Tables:**
- `processing_jobs` - Async document processing jobs
- `document_generations` - AI-generated document outputs
- `user_preferences` - Per-user AI preferences
- `conversation_summaries` - Chat conversation summaries
- `memory_entries` - Long-term memory for AI context
- `file_search_stores` - Vector store references for RAG
- `document_folders` - Document-to-folder associations
- `rag_query_cache` - Semantic query caching with pgvector Vector(768)

All tables use UUID primary keys and include `organization_id` for multi-tenant scoping. JSONB columns with GIN indexes are used for flexible metadata storage.

## GCP Resources Created

| Resource | Description |
|----------|-------------|
| **Cloud SQL** | PostgreSQL 15 instance with pgvector extension |
| **GCS Bucket** | Document storage with versioning enabled |
| **Service Account** | `document-intelligence-api-sa` with Cloud SQL, Storage, Secret Manager roles |
| **Secrets** | DATABASE_PASSWORD, JWT_SECRET_KEY, REFRESH_SECRET_KEY |

## Verifying Resources

After setup, verify all resources are created:

```bash
biz2bricks status --env-file .env
```

Expected output shows:
- Cloud SQL instance state (RUNNABLE) and IP address
- GCS bucket existence and versioning status
- Service account with IAM roles (cloudsql.client, storage.objectAdmin, secretmanager.secretAccessor)
- Secret Manager secrets (DATABASE_PASSWORD, JWT_SECRET_KEY, REFRESH_SECRET_KEY)
