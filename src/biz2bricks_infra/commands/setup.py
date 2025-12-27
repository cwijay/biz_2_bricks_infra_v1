"""
Complete environment setup orchestration.

Provides a single command to set up the entire environment:
- GCP resources (Cloud SQL, GCS, Service Account, Secrets)
- Database schema (all tables from biz2bricks_core)
- Seed data (subscription tiers)

All database tables are defined in biz2bricks_core:
- Core tables: organizations, users, folders, documents, audit_logs
- AI processing tables: processing_jobs, document_generations, memory, RAG stores
- Usage tracking tables: subscription_tiers, organization_subscriptions, token_usage_records
- RAG caching tables: rag_query_cache (with pgvector for semantic search)
"""

import asyncio
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv


# =============================================================================
# DATABASE HELPERS
# =============================================================================


async def get_db_connection():
    """Get async database connection using Cloud SQL connector or direct."""
    instance_name = os.getenv("CLOUD_SQL_INSTANCE", "")
    target_db = os.getenv("DATABASE_NAME", "doc_intelligence")
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    use_connector = os.getenv("USE_CLOUD_SQL_CONNECTOR", "true").lower() == "true"
    ip_type_str = os.getenv("CLOUD_SQL_IP_TYPE", "PUBLIC").upper()

    if use_connector and instance_name:
        try:
            from google.cloud.sql.connector import Connector, IPTypes

            ip_type = IPTypes.PUBLIC if ip_type_str == "PUBLIC" else IPTypes.PRIVATE
            loop = asyncio.get_running_loop()
            connector = Connector(loop=loop)

            conn = await connector.connect_async(
                instance_name,
                "asyncpg",
                user=db_user,
                password=db_password,
                db=target_db,
                ip_type=ip_type,
            )
            return conn, connector
        except Exception as e:
            click.echo(click.style(f"Cloud SQL Connector failed: {e}", fg="yellow"))

    # Direct connection fallback
    import asyncpg

    db_url = os.getenv("DATABASE_URL", "")
    if db_url and "@" in db_url:
        parts = db_url.split("@")
        host_part = parts[1].split("/")[0]
        host, port = host_part.split(":") if ":" in host_part else (host_part, "5432")
    else:
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")

    conn = await asyncpg.connect(
        host=host,
        port=int(port),
        user=db_user,
        password=db_password,
        database=target_db,
    )
    return conn, None


async def close_db_connection(conn, connector):
    """Close database connection."""
    if conn:
        try:
            await conn.close()
        except Exception:
            pass
    if connector:
        try:
            connector.close()
        except Exception:
            pass


async def enable_pgvector_extension(conn) -> bool:
    """Enable pgvector extension for semantic search."""
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        click.echo(click.style("  pgvector extension enabled", fg="green"))
        return True
    except Exception as e:
        click.echo(click.style(f"  Warning: Could not enable pgvector: {e}", fg="yellow"))
        click.echo("  (pgvector is optional - semantic cache will be disabled)")
        return False


async def create_vector_indexes(conn) -> bool:
    """Create IVFFlat indexes for semantic search if pgvector is available."""
    try:
        # Check if table exists first
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'rag_query_cache'
            )
        """)

        if not table_exists:
            click.echo("  rag_query_cache table not found, skipping index creation")
            return True

        # Check if pgvector extension is available
        ext_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not ext_exists:
            click.echo(click.style("  Skipping vector indexes (pgvector not enabled)", fg="yellow"))
            return False

        # Check if query_embedding column is actually a vector type (not text fallback)
        # Vector columns show as 'USER-DEFINED' in data_type
        column_type = await conn.fetchval("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'rag_query_cache' AND column_name = 'query_embedding'
        """)
        if column_type != 'USER-DEFINED':
            click.echo(click.style(
                f"  Skipping vector indexes (query_embedding is {column_type}, not vector)",
                fg="yellow"
            ))
            return False

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rag_cache_embedding
            ON rag_query_cache USING ivfflat (query_embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        click.echo(click.style("  Vector indexes created", fg="green"))
        return True
    except Exception as e:
        click.echo(click.style(f"  Warning: Could not create vector indexes: {e}", fg="yellow"))
        return False


async def get_table_count(conn) -> int:
    """Get count of tables in public schema."""
    result = await conn.fetchval("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    return result or 0


async def list_tables(conn) -> list:
    """List all tables in public schema."""
    rows = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    return [row['table_name'] for row in rows]


# =============================================================================
# SETUP STEPS
# =============================================================================


def step_check_prerequisites(project_id: str) -> bool:
    """Step 1: Check all prerequisites."""
    click.echo(click.style("\n=== Step 1: Checking Prerequisites ===", fg="blue", bold=True))

    from biz2bricks_infra.gcloud.commands import check_gcloud_auth, get_project_id

    # Check gcloud auth
    if not check_gcloud_auth():
        click.echo(click.style("  gcloud not authenticated", fg="red"))
        click.echo("  Run: gcloud auth login && gcloud auth application-default login")
        return False
    click.echo(click.style("  gcloud authenticated", fg="green"))

    # Check project
    current_project = get_project_id()
    if not current_project:
        click.echo(click.style("  GCP project not set", fg="red"))
        click.echo(f"  Run: gcloud config set project {project_id}")
        return False

    if current_project != project_id:
        click.echo(click.style(f"  Warning: Current project ({current_project}) differs from specified ({project_id})", fg="yellow"))

    click.echo(click.style(f"  Project: {current_project}", fg="green"))
    return True


def step_force_delete(env_file: str, dry_run: bool) -> bool:
    """Step 1.5: Force delete existing resources before recreation."""
    click.echo(click.style("\n=== Step 1.5: Deleting Existing Resources (--force) ===", fg="red", bold=True))

    click.echo(click.style(
        "\n  WARNING: This will DELETE ALL existing GCP resources:",
        fg="red",
        bold=True
    ))
    click.echo("    - Secret Manager secrets (DATABASE_PASSWORD, JWT_SECRET_KEY, REFRESH_SECRET_KEY)")
    click.echo("    - Service Account and IAM bindings")
    click.echo("    - GCS Bucket and ALL contents")
    click.echo("    - Cloud SQL instance and ALL data")
    click.echo("")

    if dry_run:
        click.echo(click.style("  [DRY RUN] Would delete all resources listed above", fg="yellow"))
        click.echo(click.style("  [DRY RUN] Then would recreate them with new configuration", fg="yellow"))
        return True

    # Require explicit confirmation for destructive operation
    confirmation = click.prompt(
        click.style("  Type 'DELETE' to confirm", fg="red"),
        default=""
    )

    if confirmation != "DELETE":
        click.echo(click.style("  Aborted. Resources were NOT deleted.", fg="yellow"))
        return False

    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=False)

    if not provisioner.config:
        click.echo(click.style("  Could not load configuration", fg="red"))
        return False

    # Delete in reverse dependency order
    success = provisioner.delete_all()

    if success:
        click.echo(click.style("  All existing resources deleted successfully", fg="green"))
    else:
        click.echo(click.style("  Some resources could not be deleted (may not have existed)", fg="yellow"))

    return True  # Continue even if some deletions "failed" (resources may not exist)


def step_provision_gcp(env_file: str, dry_run: bool) -> bool:
    """Step 2: Provision GCP resources."""
    click.echo(click.style("\n=== Step 2: Provisioning GCP Resources ===", fg="blue", bold=True))

    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)

    if not provisioner.check_prerequisites():
        return False

    return provisioner.provision_all()


def step_generate_env(
    output: str,
    project_id: str,
    region: str,
    db_password: str | None = None,
    jwt_secret: str | None = None,
    refresh_secret: str | None = None,
) -> bool:
    """Step 3: Generate .env file."""
    click.echo(click.style("\n=== Step 3: Generating Environment File ===", fg="blue", bold=True))

    from biz2bricks_infra.provision.env_generator import generate_env_file

    return generate_env_file(
        output, project_id, region,
        db_password=db_password,
        jwt_secret=jwt_secret,
        refresh_secret=refresh_secret,
    )


def step_create_tables(env_file: str) -> bool:
    """Step 4: Create database tables.

    All models are now defined in biz2bricks_core, including:
    - Core tables: organizations, users, folders, documents, audit_logs
    - AI processing tables: processing_jobs, document_generations, memory, RAG
    - Usage tracking tables: subscription_tiers, organization_subscriptions, token_usage_records
    - RAG caching tables: rag_query_cache (with pgvector)
    """
    click.echo(click.style("\n=== Step 4: Creating Database Tables ===", fg="blue", bold=True))

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        from biz2bricks_core import db, Base
        # Import all models to ensure they're registered with Base
        from biz2bricks_core import (
            # Core
            OrganizationModel, UserModel, FolderModel, DocumentModel, AuditLogModel,
            # Usage/billing
            SubscriptionTierModel, OrganizationSubscriptionModel,
            TokenUsageRecordModel, ResourceUsageRecordModel, UsageAggregationModel,
        )
        click.echo(click.style("  Loaded all models from biz2bricks_core", fg="green"))

        async def create():
            click.echo("  Testing database connection...")
            if not await db.test_connection():
                click.echo(click.style("  Could not connect to database", fg="red"))
                return False

            click.echo(click.style("  Connection successful!", fg="green"))

            # Enable pgvector
            conn, connector = await get_db_connection()
            try:
                await enable_pgvector_extension(conn)
            finally:
                await close_db_connection(conn, connector)

            # Create tables
            click.echo("  Creating tables...")
            await db.create_tables()

            # List created tables
            conn, connector = await get_db_connection()
            try:
                tables = await list_tables(conn)
                click.echo(click.style(f"  Created {len(tables)} tables:", fg="green"))
                for table in tables:
                    click.echo(f"    - {table}")

                # Create vector indexes
                await create_vector_indexes(conn)
            finally:
                await close_db_connection(conn, connector)

            await db.close_all()
            return True

        return asyncio.run(create())

    except ImportError as e:
        click.echo(click.style(f"  biz2bricks-core not installed: {e}", fg="red"))
        return False
    except Exception as e:
        click.echo(click.style(f"  Error: {e}", fg="red"))
        return False


def step_seed_tiers(env_file: str) -> bool:
    """Step 5: Seed subscription tiers."""
    click.echo(click.style("\n=== Step 5: Seeding Subscription Tiers ===", fg="blue", bold=True))

    from biz2bricks_infra.commands.seed import seed_tiers_async, list_tiers_async

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    async def run_seed_steps():
        """Run seed and list in single async context to avoid connector cleanup issues."""
        await seed_tiers_async()
        await list_tiers_async()

    try:
        asyncio.run(run_seed_steps())
        return True
    except Exception as e:
        click.echo(click.style(f"  Error seeding tiers: {e}", fg="red"))
        return False


async def validate_setup_async() -> bool:
    """Validate the setup (async version)."""
    click.echo(click.style("\n=== Step 6: Validating Setup ===", fg="blue", bold=True))

    conn, connector = await get_db_connection()
    try:
        # Check tables
        table_count = await get_table_count(conn)
        click.echo(f"  Tables created: {table_count}")

        # Check subscription tiers
        tier_count = await conn.fetchval("SELECT COUNT(*) FROM subscription_tiers")
        click.echo(f"  Subscription tiers: {tier_count}")

        # Check pgvector
        try:
            await conn.execute("SELECT 'test'::vector(3)")
            click.echo(click.style("  pgvector: enabled", fg="green"))
        except Exception:
            click.echo(click.style("  pgvector: not available", fg="yellow"))

        return True
    except Exception as e:
        click.echo(click.style(f"  Validation error: {e}", fg="red"))
        return False
    finally:
        await close_db_connection(conn, connector)


def step_validate(env_file: str) -> bool:
    """Step 6: Validate the setup."""
    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        return asyncio.run(validate_setup_async())
    except Exception as e:
        click.echo(click.style(f"  Error: {e}", fg="red"))
        return False


async def run_database_setup_workflow(
    env_file: str,
    skip_db: bool,
    skip_seed: bool,
    skip_validation: bool,
) -> dict:
    """Run all database operations in a single async context.

    This avoids multiple asyncio.run() calls which cause unclosed
    client session warnings with Cloud SQL connectors.
    """
    from biz2bricks_infra.commands.seed import seed_tiers_async, list_tiers_async

    results = {}

    # Step 4: Create tables
    if not skip_db:
        click.echo(click.style("\n=== Step 4: Creating Database Tables ===", fg="blue", bold=True))
        try:
            from biz2bricks_core import db, Base
            from biz2bricks_core import (
                OrganizationModel, UserModel, FolderModel, DocumentModel, AuditLogModel,
                SubscriptionTierModel, OrganizationSubscriptionModel,
                TokenUsageRecordModel, ResourceUsageRecordModel, UsageAggregationModel,
            )
            click.echo(click.style("  Loaded all models from biz2bricks_core", fg="green"))

            click.echo("  Testing database connection...")
            if not await db.test_connection():
                click.echo(click.style("  Could not connect to database", fg="red"))
                results["db"] = False
                return results

            click.echo(click.style("  Connection successful!", fg="green"))

            # Enable pgvector
            conn, connector = await get_db_connection()
            try:
                await enable_pgvector_extension(conn)
            finally:
                await close_db_connection(conn, connector)

            # Create tables
            click.echo("  Creating tables...")
            await db.create_tables()

            # List created tables and create indexes
            conn, connector = await get_db_connection()
            try:
                tables = await list_tables(conn)
                click.echo(click.style(f"  Created {len(tables)} tables:", fg="green"))
                for table in tables:
                    click.echo(f"    - {table}")
                await create_vector_indexes(conn)
            finally:
                await close_db_connection(conn, connector)

            await db.close_all()
            # Allow time for connection cleanup to complete
            await asyncio.sleep(0.1)
            results["db"] = True

        except ImportError as e:
            click.echo(click.style(f"  biz2bricks-core not installed: {e}", fg="red"))
            results["db"] = False
            return results
        except Exception as e:
            click.echo(click.style(f"  Error: {e}", fg="red"))
            results["db"] = False
            return results
    else:
        click.echo(click.style("\n=== Step 4: Skipping Database Table Creation ===", fg="yellow"))
        results["db"] = "skipped"

    if not results.get("db") and results.get("db") is not None and results["db"] != "skipped":
        return results

    # Step 5: Seed tiers
    if not skip_seed:
        click.echo(click.style("\n=== Step 5: Seeding Subscription Tiers ===", fg="blue", bold=True))
        try:
            await seed_tiers_async()
            await list_tiers_async()
            results["seed"] = True
        except Exception as e:
            click.echo(click.style(f"  Error seeding tiers: {e}", fg="red"))
            results["seed"] = False
            return results
    else:
        click.echo(click.style("\n=== Step 5: Skipping Subscription Tier Seeding ===", fg="yellow"))
        results["seed"] = "skipped"

    # Step 6: Validate
    if not skip_validation:
        results["validation"] = await validate_setup_async()
    else:
        click.echo(click.style("\n=== Step 6: Skipping Validation ===", fg="yellow"))
        results["validation"] = "skipped"

    # Allow time for all connection cleanups to complete before event loop exits
    await asyncio.sleep(0.2)

    return results


# =============================================================================
# CLI COMMANDS
# =============================================================================


@click.group()
def setup():
    """Complete environment setup commands."""
    pass


@setup.command("all")
@click.option("--project-id", required=True, help="GCP project ID")
@click.option("--region", default="us-central1", help="GCP region")
@click.option("--env-file", default=".env.production", help="Provisioning config file")
@click.option("--output-env", default=".env", help="Output .env file for app")
@click.option("--dry-run", is_flag=True, help="Preview actions without executing")
@click.option("--skip-gcp", is_flag=True, help="Skip GCP resource provisioning")
@click.option("--skip-db", is_flag=True, help="Skip database table creation")
@click.option("--skip-seed", is_flag=True, help="Skip subscription tier seeding")
@click.option("--skip-validation", is_flag=True, help="Skip final validation")
@click.option("--force", is_flag=True, help="Delete existing resources before creating (destructive!)")
def setup_all(
    project_id: str,
    region: str,
    env_file: str,
    output_env: str,
    dry_run: bool,
    skip_gcp: bool,
    skip_db: bool,
    skip_seed: bool,
    skip_validation: bool,
    force: bool,
):
    """Complete one-command setup: GCP resources + database + seed data.

    \b
    This command orchestrates the entire environment setup:
    1. Check prerequisites (gcloud auth, project access)
    1.5. [--force] Delete existing resources before recreation
    2. Provision GCP resources (Cloud SQL, GCS, Service Account, Secrets)
    3. Generate .env file from provisioned resources
    4. Create database tables (all models including pgvector support)
    5. Seed subscription tiers (Free, Pro, Enterprise)
    6. Validate the setup

    \b
    Examples:
        # Full setup for a new environment
        biz2bricks setup all --project-id my-project

        # Preview what would be done
        biz2bricks setup all --project-id my-project --dry-run

        # Force recreate all resources (deletes existing first!)
        biz2bricks setup all --project-id my-project --force

        # Preview force recreation
        biz2bricks setup all --project-id my-project --force --dry-run

        # Skip GCP provisioning (resources already exist)
        biz2bricks setup all --project-id my-project --skip-gcp

        # Only database setup (skip GCP and seeding)
        biz2bricks setup all --project-id my-project --skip-gcp --skip-seed
    """
    click.echo(click.style("=" * 60, fg="blue"))
    click.echo(click.style("  Biz2Bricks Complete Environment Setup", fg="blue", bold=True))
    click.echo(click.style("=" * 60, fg="blue"))
    click.echo(f"  Project: {project_id}")
    click.echo(f"  Region: {region}")
    click.echo(f"  Dry Run: {dry_run}")
    click.echo(f"  Force: {force}")
    click.echo(f"  Skip GCP: {skip_gcp}")
    click.echo(f"  Skip DB: {skip_db}")
    click.echo(f"  Skip Seed: {skip_seed}")

    results = {}

    # Step 1: Prerequisites
    results["prerequisites"] = step_check_prerequisites(project_id)
    if not results["prerequisites"]:
        click.echo(click.style("\nSetup failed at prerequisites check.", fg="red"))
        sys.exit(1)

    # Step 1.5: Force Delete (if --force is set)
    if force and not skip_gcp:
        results["force_delete"] = step_force_delete(env_file, dry_run)
        if not results["force_delete"]:
            click.echo(click.style("\nSetup aborted.", fg="red"))
            sys.exit(1)

    # Step 2: GCP Provisioning
    if not skip_gcp:
        results["gcp"] = step_provision_gcp(env_file, dry_run)
        if not results["gcp"]:
            click.echo(click.style("\nSetup failed at GCP provisioning.", fg="red"))
            click.echo("Fix the issues and re-run with --skip-gcp to continue from database setup.")
            sys.exit(1)
    else:
        click.echo(click.style("\n=== Step 2: Skipping GCP Provisioning ===", fg="yellow"))
        results["gcp"] = "skipped"

    # Step 3: Generate .env
    if not skip_gcp and not dry_run:
        # Load config to get secrets from source env file
        from biz2bricks_infra.provision.config import ProvisioningConfig
        config = ProvisioningConfig.from_env_file(env_file)

        results["env"] = step_generate_env(
            output_env, project_id, region,
            db_password=config.database_password,
            jwt_secret=config.jwt_secret_key,
            refresh_secret=config.refresh_secret_key,
        )
    else:
        click.echo(click.style("\n=== Step 3: Skipping Environment File Generation ===", fg="yellow"))
        results["env"] = "skipped"

    # Steps 4-6: Database operations (run in single async context to avoid connector issues)
    if not dry_run and (not skip_db or not skip_seed or not skip_validation):
        db_env = output_env if not skip_gcp else env_file

        # Load environment for database operations
        env_path = Path(db_env)
        if env_path.exists():
            load_dotenv(env_path)

        try:
            # Run all database operations in single async context
            db_results = asyncio.run(run_database_setup_workflow(
                env_file=db_env,
                skip_db=skip_db,
                skip_seed=skip_seed,
                skip_validation=skip_validation,
            ))
            results.update(db_results)

            # Check for failures
            if results.get("db") is False:
                click.echo(click.style("\nSetup failed at database table creation.", fg="red"))
                click.echo("Fix the issues and re-run with --skip-gcp --skip-db to continue from seeding.")
                sys.exit(1)

            if results.get("seed") is False:
                click.echo(click.style("\nSetup failed at tier seeding.", fg="red"))
                sys.exit(1)

        except Exception as e:
            click.echo(click.style(f"\nDatabase setup error: {e}", fg="red"))
            sys.exit(1)
    else:
        if dry_run or skip_db:
            click.echo(click.style("\n=== Step 4: Skipping Database Table Creation ===", fg="yellow"))
            results["db"] = "skipped"
        if dry_run or skip_seed:
            click.echo(click.style("\n=== Step 5: Skipping Subscription Tier Seeding ===", fg="yellow"))
            results["seed"] = "skipped"
        if dry_run or skip_validation:
            click.echo(click.style("\n=== Step 6: Skipping Validation ===", fg="yellow"))
            results["validation"] = "skipped"

    # Summary
    click.echo(click.style("\n" + "=" * 60, fg="blue"))
    click.echo(click.style("  Setup Complete!", fg="green", bold=True))
    click.echo(click.style("=" * 60, fg="blue"))

    for step, result in results.items():
        if result == "skipped":
            status = click.style("SKIPPED", fg="yellow")
        elif result:
            status = click.style("SUCCESS", fg="green")
        else:
            status = click.style("FAILED", fg="red")
        click.echo(f"  {step}: {status}")

    if not dry_run:
        click.echo(f"\n  Generated environment file: {output_env}")
        click.echo("\n  Next steps:")
        click.echo(f"    1. Review {output_env} and update any values as needed")
        click.echo("    2. Start your application: uvicorn src.main:app --reload")


@setup.command("db-only")
@click.option("--env-file", default=".env", help="Environment file")
def setup_db_only(env_file: str):
    """Create database tables only (no GCP provisioning).

    Use this when GCP resources already exist and you just need
    to create or recreate the database schema.

    All tables are created from biz2bricks_core models, including:
    - Core tables: organizations, users, folders, documents, audit_logs
    - AI processing tables: processing_jobs, document_generations, memory
    - Usage tracking tables: subscription_tiers, organization_subscriptions, token_usage_records
    - RAG caching tables: rag_query_cache (with pgvector)
    """
    click.echo(click.style("Database-only Setup", fg="blue", bold=True))

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        click.echo(f"Loaded environment from: {env_path}")

    success = step_create_tables(env_file)

    if success:
        click.echo(click.style("\nDatabase setup complete!", fg="green"))
        sys.exit(0)
    else:
        click.echo(click.style("\nDatabase setup failed.", fg="red"))
        sys.exit(1)
