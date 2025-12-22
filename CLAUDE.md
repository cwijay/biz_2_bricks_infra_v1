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
# Provision GCP resources
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
biz2bricks db reset --force         # Drop ALL tables and recreate schema (destructive!)

# Alembic migrations (via biz2bricks-core)
biz2bricks migrate upgrade head     # Apply all pending migrations
biz2bricks migrate downgrade -1     # Rollback one migration
biz2bricks migrate current          # Show current migration revision
biz2bricks migrate history          # Show migration history

# Utilities
biz2bricks generate-env --project-id PROJECT  # Generate .env from provisioned resources
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
├── cli.py                 # Click-based CLI entry point (provision, migrate, generate-env commands)
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

The database includes 17 tables from biz2bricks_core, organized into three modules:

**Core Tables:**
- `organizations` - Multi-tenant organization data
- `users` - User accounts (scoped by organization)
- `folders` - Document folder hierarchy
- `documents` - Document metadata and content
- `audit_logs` - Audit trail for all operations

**Usage/Billing Tables:**
- `usage_events` - Individual usage events
- `usage_daily_summary` - Aggregated daily usage
- `usage_limits` - Per-organization usage limits
- `model_pricing` - AI model pricing configuration
- `subscription_plans` - Subscription tier definitions

**AI Module Tables (doc_intelligence_ai_v3.0):**
- `processing_jobs` - Async document processing jobs
- `document_generations` - AI-generated document outputs
- `user_preferences` - Per-user AI preferences
- `conversation_summaries` - Chat conversation summaries
- `memory_entries` - Long-term memory for AI context
- `file_search_stores` - Vector store references for RAG
- `document_folders` - Document-to-folder associations

All tables use UUID primary keys and include `organization_id` for multi-tenant scoping. JSONB columns with GIN indexes are used for flexible metadata storage.
