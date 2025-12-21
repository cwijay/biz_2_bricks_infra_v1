# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is `biz2bricks-infra`, a Python CLI tool that provisions GCP infrastructure using gcloud/gsutil commands (not Terraform). It creates Cloud SQL PostgreSQL instances, GCS buckets, service accounts, and Secret Manager secrets.

## Commands

### Installation
```bash
ssh -T git@github.com               # Verify SSH auth (biz2bricks-core is private repo)
pip install -e .                    # Install (fetches biz2bricks-core from GitHub)
pip install -e ".[dev]"             # Include dev dependencies (pytest, black, ruff, mypy)
```

### CLI Usage
```bash
biz2bricks provision full-setup     # Provision all GCP resources
biz2bricks provision full-setup --dry-run  # Preview without executing
biz2bricks provision cloud-sql      # Only Cloud SQL
biz2bricks provision gcs-bucket     # Only GCS bucket
biz2bricks provision service-account # Only service account
biz2bricks provision secrets        # Only secrets

biz2bricks migrate upgrade head     # Run database migrations (via biz2bricks-core)
biz2bricks migrate current          # Show current migration
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
