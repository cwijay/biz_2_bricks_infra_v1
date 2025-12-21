"""
CLI entry point for biz2bricks infrastructure tools.

Commands:
    biz2bricks provision --full-setup   # Provision all GCP resources
    biz2bricks migrate upgrade head     # Run database migrations
    biz2bricks generate-env             # Generate .env file from GCP
"""

import click
import subprocess
import sys
from pathlib import Path


@click.group()
@click.version_option()
def main():
    """Biz2Bricks Infrastructure CLI - Provision GCP resources and manage migrations."""
    pass


# =============================================================================
# Provision Commands
# =============================================================================


@main.group()
def provision():
    """Provision GCP resources."""
    pass


@provision.command("full-setup")
@click.option("--env-file", default=".env.production", help="Environment file to read config from")
@click.option("--dry-run", is_flag=True, help="Preview actions without executing")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def full_setup(env_file: str, dry_run: bool, force: bool):
    """Provision all GCP resources (Cloud SQL, GCS, Service Account, Secrets)."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)

    if not provisioner.check_prerequisites():
        click.echo(click.style("Prerequisites check failed. Aborting.", fg="red"))
        sys.exit(1)

    if not dry_run and not force:
        click.confirm("This will provision GCP resources. Continue?", abort=True)

    success = provisioner.provision_all()
    sys.exit(0 if success else 1)


@provision.command("cloud-sql")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--dry-run", is_flag=True, help="Preview only")
def cloud_sql(env_file: str, dry_run: bool):
    """Provision Cloud SQL PostgreSQL instance."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)
    success = provisioner.provision_cloud_sql()
    sys.exit(0 if success else 1)


@provision.command("gcs-bucket")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--dry-run", is_flag=True, help="Preview only")
def gcs_bucket(env_file: str, dry_run: bool):
    """Provision GCS bucket."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)
    success = provisioner.provision_gcs_bucket()
    sys.exit(0 if success else 1)


@provision.command("service-account")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--dry-run", is_flag=True, help="Preview only")
def service_account(env_file: str, dry_run: bool):
    """Provision service account with IAM roles."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)
    success = provisioner.provision_service_account()
    sys.exit(0 if success else 1)


@provision.command("secrets")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--dry-run", is_flag=True, help="Preview only")
def secrets(env_file: str, dry_run: bool):
    """Provision Secret Manager secrets."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=dry_run)
    success = provisioner.provision_secrets()
    sys.exit(0 if success else 1)


# =============================================================================
# Status Commands
# =============================================================================


@main.command("status")
@click.option("--env-file", default=".env.production", help="Environment file")
def status(env_file: str):
    """Show status of all provisioned GCP resources."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    provisioner = Provisioner(env_file=env_file, dry_run=True)
    provisioner.show_status()


# =============================================================================
# Delete Commands
# =============================================================================


@main.group()
def delete():
    """Delete provisioned GCP resources (use with caution!)."""
    pass


@delete.command("all")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def delete_all(env_file: str, force: bool):
    """Delete ALL provisioned GCP resources."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    if not force:
        click.confirm(
            click.style("WARNING: This will delete ALL resources. Continue?", fg="red"),
            abort=True,
        )

    provisioner = Provisioner(env_file=env_file, dry_run=False)
    success = provisioner.delete_all()
    sys.exit(0 if success else 1)


@delete.command("cloud-sql")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_cloud_sql(env_file: str, force: bool):
    """Delete Cloud SQL instance."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    if not force:
        click.confirm("Delete Cloud SQL instance?", abort=True)

    provisioner = Provisioner(env_file=env_file, dry_run=False)
    success = provisioner.delete_cloud_sql()
    sys.exit(0 if success else 1)


@delete.command("gcs-bucket")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_gcs_bucket(env_file: str, force: bool):
    """Delete GCS bucket."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    if not force:
        click.confirm("Delete GCS bucket and all contents?", abort=True)

    provisioner = Provisioner(env_file=env_file, dry_run=False)
    success = provisioner.delete_gcs_bucket()
    sys.exit(0 if success else 1)


@delete.command("service-account")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_service_account(env_file: str, force: bool):
    """Delete service account."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    if not force:
        click.confirm("Delete service account?", abort=True)

    provisioner = Provisioner(env_file=env_file, dry_run=False)
    success = provisioner.delete_service_account()
    sys.exit(0 if success else 1)


@delete.command("secrets")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_secrets(env_file: str, force: bool):
    """Delete Secret Manager secrets."""
    from biz2bricks_infra.provision.provisioner import Provisioner

    if not force:
        click.confirm("Delete all secrets?", abort=True)

    provisioner = Provisioner(env_file=env_file, dry_run=False)
    success = provisioner.delete_secrets()
    sys.exit(0 if success else 1)


# =============================================================================
# Secrets Commands
# =============================================================================


@main.group("secrets")
def secrets_group():
    """Secret Manager operations."""
    pass


@secrets_group.command("get")
@click.argument("secret_name")
@click.option("--project-id", help="GCP project ID (defaults to current)")
def secrets_get(secret_name: str, project_id: str):
    """Get a secret value from Secret Manager."""
    from biz2bricks_infra.gcloud.commands import run_gcloud_command, get_project_id

    project = project_id or get_project_id()
    if not project:
        click.echo(click.style("Could not determine project ID", fg="red"))
        sys.exit(1)

    success, output = run_gcloud_command([
        "secrets", "versions", "access", "latest",
        "--secret", secret_name,
        "--project", project,
    ])

    if success:
        click.echo(output)
    else:
        click.echo(click.style(f"Failed to get secret: {output}", fg="red"))
        sys.exit(1)


@secrets_group.command("list")
@click.option("--project-id", help="GCP project ID (defaults to current)")
def secrets_list(project_id: str):
    """List all secrets in Secret Manager."""
    from biz2bricks_infra.gcloud.commands import run_gcloud_command, get_project_id

    project = project_id or get_project_id()
    if not project:
        click.echo(click.style("Could not determine project ID", fg="red"))
        sys.exit(1)

    success, output = run_gcloud_command([
        "secrets", "list",
        "--project", project,
        "--format=table(name,createTime)",
    ])

    if success:
        click.echo(output)
    else:
        click.echo(click.style(f"Failed to list secrets: {output}", fg="red"))
        sys.exit(1)


# =============================================================================
# Service Account Commands
# =============================================================================


@main.group("sa")
def sa_group():
    """Service account operations."""
    pass


@sa_group.command("create-key")
@click.option("--env-file", default=".env.production", help="Environment file")
@click.option("--output", "-o", default="service-account-key.json", help="Output key file")
def sa_create_key(env_file: str, output: str):
    """Create a JSON key file for the service account."""
    from biz2bricks_infra.provision.config import ProvisioningConfig
    from biz2bricks_infra.gcloud.commands import run_gcloud_command

    try:
        config = ProvisioningConfig.from_env_file(env_file)
    except (FileNotFoundError, ValueError) as e:
        click.echo(click.style(f"Error loading config: {e}", fg="red"))
        sys.exit(1)

    sa_email = f"{config.service_account_name}@{config.project_id}.iam.gserviceaccount.com"

    click.echo(f"Creating key for service account: {sa_email}")

    success, result = run_gcloud_command([
        "iam", "service-accounts", "keys", "create", output,
        "--iam-account", sa_email,
        "--project", config.project_id,
    ])

    if success:
        click.echo(click.style(f"Key created: {output}", fg="green"))
        click.echo(click.style("WARNING: Keep this file secure and do not commit to git!", fg="yellow"))
    else:
        click.echo(click.style(f"Failed to create key: {result}", fg="red"))
        sys.exit(1)


@sa_group.command("list-keys")
@click.option("--env-file", default=".env.production", help="Environment file")
def sa_list_keys(env_file: str):
    """List keys for the service account."""
    from biz2bricks_infra.provision.config import ProvisioningConfig
    from biz2bricks_infra.gcloud.commands import run_gcloud_command

    try:
        config = ProvisioningConfig.from_env_file(env_file)
    except (FileNotFoundError, ValueError) as e:
        click.echo(click.style(f"Error loading config: {e}", fg="red"))
        sys.exit(1)

    sa_email = f"{config.service_account_name}@{config.project_id}.iam.gserviceaccount.com"

    success, output = run_gcloud_command([
        "iam", "service-accounts", "keys", "list",
        "--iam-account", sa_email,
        "--project", config.project_id,
        "--format=table(name.basename(),validAfterTime,validBeforeTime)",
    ])

    if success:
        click.echo(output)
    else:
        click.echo(click.style(f"Failed to list keys: {output}", fg="red"))
        sys.exit(1)


# =============================================================================
# Database Commands
# =============================================================================


@main.group("db")
def db_group():
    """Database operations."""
    pass


@db_group.command("init")
@click.option("--env-file", default=".env", help="Environment file for database config")
def db_init(env_file: str):
    """Initialize database tables using biz2bricks_core models."""
    import asyncio
    from pathlib import Path
    from dotenv import load_dotenv
    import os

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        click.echo(f"Loaded environment from: {env_path}")

    try:
        from biz2bricks_core import db, Base

        async def init_tables():
            click.echo("Testing database connection...")
            if not await db.test_connection():
                click.echo(click.style("Could not connect to database", fg="red"))
                return False

            click.echo(click.style("Connection successful!", fg="green"))
            click.echo("Creating tables...")

            await db.create_tables()
            click.echo(click.style("Tables created successfully!", fg="green"))

            await db.close_all()
            return True

        success = asyncio.run(init_tables())
        sys.exit(0 if success else 1)

    except ImportError:
        click.echo(click.style("biz2bricks-core not installed. Install it first.", fg="red"))
        sys.exit(1)


@db_group.command("status")
@click.option("--env-file", default=".env", help="Environment file for database config")
def db_status(env_file: str):
    """Show database status and table information."""
    import asyncio
    from pathlib import Path
    from dotenv import load_dotenv

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        from biz2bricks_core import db
        from sqlalchemy import text

        async def show_status():
            if not await db.test_connection():
                click.echo(click.style("Could not connect to database", fg="red"))
                return False

            engine = await db.get_engine_async()
            async with engine.connect() as conn:
                # Get PostgreSQL version
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                click.echo(f"PostgreSQL: {version[:50]}...")

                # Get tables
                result = await conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' ORDER BY table_name
                """))
                tables = result.fetchall()

                if tables:
                    click.echo("\nTables:")
                    for (table_name,) in tables:
                        count_result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                        count = count_result.scalar()
                        click.echo(f"  - {table_name}: {count} rows")
                else:
                    click.echo("No tables found. Run 'biz2bricks db init' to create tables.")

            await db.close_all()
            return True

        asyncio.run(show_status())

    except ImportError:
        click.echo(click.style("biz2bricks-core not installed", fg="red"))
        sys.exit(1)


# =============================================================================
# Migration Commands
# =============================================================================


@main.group()
def migrate():
    """Database migration commands (wraps Alembic)."""
    pass


@migrate.command("upgrade")
@click.argument("revision", default="head")
def upgrade(revision: str):
    """Upgrade database to a revision (default: head)."""
    _run_alembic(["upgrade", revision])


@migrate.command("downgrade")
@click.argument("revision", default="-1")
def downgrade(revision: str):
    """Downgrade database by revision (default: -1)."""
    _run_alembic(["downgrade", revision])


@migrate.command("current")
def current():
    """Show current migration revision."""
    _run_alembic(["current"])


@migrate.command("history")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def history(verbose: bool):
    """Show migration history."""
    args = ["history"]
    if verbose:
        args.append("--verbose")
    _run_alembic(args)


@migrate.command("revision")
@click.option("--message", "-m", required=True, help="Revision message")
@click.option("--autogenerate", is_flag=True, help="Auto-generate from model changes")
def revision(message: str, autogenerate: bool):
    """Create a new migration revision."""
    args = ["revision", "-m", message]
    if autogenerate:
        args.append("--autogenerate")
    _run_alembic(args)


def _run_alembic(args: list):
    """Run alembic command from biz2bricks-core package."""
    # Find biz2bricks-core package location
    try:
        import biz2bricks_core

        core_path = Path(biz2bricks_core.__file__).parent.parent.parent
        alembic_ini = core_path / "alembic.ini"

        if not alembic_ini.exists():
            click.echo(click.style(f"alembic.ini not found at {alembic_ini}", fg="red"))
            sys.exit(1)

        cmd = ["alembic", "-c", str(alembic_ini)] + args
        result = subprocess.run(cmd, cwd=str(core_path))
        sys.exit(result.returncode)
    except ImportError:
        click.echo(
            click.style("biz2bricks-core package not found. Install it first.", fg="red")
        )
        sys.exit(1)


# =============================================================================
# Usage Tracking Commands
# =============================================================================


@main.group()
def usage():
    """Usage tracking and reporting commands."""
    pass


@usage.command("storage")
@click.option("--org-id", required=True, help="Organization ID")
@click.option("--env-file", default=".env", help="Environment file")
def usage_storage(org_id: str, env_file: str):
    """Show storage usage for an organization."""
    import asyncio
    from pathlib import Path
    from dotenv import load_dotenv

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        from biz2bricks_core import usage_service, db

        async def show_storage():
            await db.get_engine_async()
            result = await usage_service.check_storage_limit(org_id)

            current_mb = result.current_bytes / (1024 * 1024)
            limit_mb = (result.limit_bytes or 0) / (1024 * 1024)
            remaining_mb = (result.remaining_bytes or 0) / (1024 * 1024)

            click.echo(click.style("\n=== Storage Usage ===", fg="blue", bold=True))
            click.echo(f"Organization: {org_id}")
            click.echo(f"Tier: {result.tier}")
            click.echo(f"Storage Used: {current_mb:.2f} MB")
            click.echo(f"Storage Limit: {limit_mb:.2f} MB")
            click.echo(f"Remaining: {remaining_mb:.2f} MB")
            click.echo(f"Percentage Used: {result.percentage_used:.1f}%")

            if result.percentage_used >= 90:
                click.echo(click.style("\nWARNING: Storage almost full!", fg="red", bold=True))
            elif result.percentage_used >= 80:
                click.echo(click.style("\nWARNING: Approaching storage limit!", fg="yellow"))
            else:
                click.echo(click.style("\nStatus: OK", fg="green"))

            await db.close_all()

        asyncio.run(show_storage())

    except ImportError:
        click.echo(click.style("biz2bricks-core not installed", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@usage.command("tokens")
@click.option("--org-id", required=True, help="Organization ID")
@click.option("--days", default=30, help="Number of days to report")
@click.option("--env-file", default=".env", help="Environment file")
def usage_tokens(org_id: str, days: int, env_file: str):
    """Show token usage for an organization."""
    import asyncio
    from pathlib import Path
    from datetime import datetime, timedelta
    from dotenv import load_dotenv

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        from biz2bricks_core import db
        from biz2bricks_core.models.usage import UsageEventModel
        from sqlalchemy import select, func

        async def show_tokens():
            await db.get_engine_async()
            cutoff = datetime.utcnow() - timedelta(days=days)

            async with db.session() as session:
                stmt = select(
                    func.count(UsageEventModel.id).label("total_requests"),
                    func.sum(UsageEventModel.input_tokens).label("total_input"),
                    func.sum(UsageEventModel.output_tokens).label("total_output"),
                    func.sum(UsageEventModel.input_cost + UsageEventModel.output_cost).label("total_cost"),
                ).where(
                    UsageEventModel.organization_id == org_id,
                    UsageEventModel.created_at >= cutoff
                )

                result = await session.execute(stmt)
                row = result.first()

                click.echo(click.style("\n=== Token Usage ===", fg="blue", bold=True))
                click.echo(f"Organization: {org_id}")
                click.echo(f"Period: Last {days} days")
                click.echo(f"Total Requests: {row.total_requests or 0:,}")
                click.echo(f"Input Tokens: {row.total_input or 0:,}")
                click.echo(f"Output Tokens: {row.total_output or 0:,}")
                click.echo(f"Total Tokens: {(row.total_input or 0) + (row.total_output or 0):,}")
                click.echo(f"Total Cost: ${float(row.total_cost or 0):.4f}")

                # Get breakdown by feature
                feature_stmt = select(
                    UsageEventModel.feature,
                    func.sum(UsageEventModel.input_tokens + UsageEventModel.output_tokens).label("tokens"),
                    func.count(UsageEventModel.id).label("requests"),
                ).where(
                    UsageEventModel.organization_id == org_id,
                    UsageEventModel.created_at >= cutoff
                ).group_by(UsageEventModel.feature)

                feature_result = await session.execute(feature_stmt)
                features = feature_result.fetchall()

                if features:
                    click.echo(click.style("\nBy Feature:", fg="cyan"))
                    for feature, tokens, requests in features:
                        click.echo(f"  {feature}: {tokens or 0:,} tokens ({requests} requests)")

            await db.close_all()

        asyncio.run(show_tokens())

    except ImportError:
        click.echo(click.style("biz2bricks-core not installed", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@usage.command("recalculate-storage")
@click.option("--org-id", help="Organization ID (or use --all)")
@click.option("--all", "all_orgs", is_flag=True, help="Recalculate for all organizations")
@click.option("--env-file", default=".env", help="Environment file")
def usage_recalculate(org_id: str, all_orgs: bool, env_file: str):
    """Recalculate storage usage from documents table."""
    import asyncio
    from pathlib import Path
    from dotenv import load_dotenv

    if not org_id and not all_orgs:
        click.echo(click.style("Specify --org-id or --all", fg="red"))
        sys.exit(1)

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)

    try:
        from biz2bricks_core import db, usage_service, OrganizationModel
        from sqlalchemy import select

        async def recalculate():
            await db.get_engine_async()

            if all_orgs:
                async with db.session() as session:
                    result = await session.execute(select(OrganizationModel.id))
                    org_ids = [row[0] for row in result.fetchall()]
            else:
                org_ids = [org_id]

            click.echo(click.style("\n=== Recalculating Storage ===", fg="blue", bold=True))
            for oid in org_ids:
                storage = await usage_service.recalculate_storage(oid)
                mb = storage / (1024 * 1024)
                click.echo(f"  {oid}: {mb:.2f} MB")

            await db.close_all()
            click.echo(click.style("\nRecalculation complete!", fg="green"))

        asyncio.run(recalculate())

    except ImportError:
        click.echo(click.style("biz2bricks-core not installed", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


# =============================================================================
# Environment File Commands
# =============================================================================


@main.command("generate-env")
@click.option("--output", "-o", default=".env", help="Output file path")
@click.option("--project-id", required=True, help="GCP project ID")
@click.option("--region", default="us-central1", help="GCP region")
def generate_env(output: str, project_id: str, region: str):
    """Generate .env file from provisioned GCP resources."""
    from biz2bricks_infra.provision.env_generator import generate_env_file

    success = generate_env_file(output, project_id, region)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
