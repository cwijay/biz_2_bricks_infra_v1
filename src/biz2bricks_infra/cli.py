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


@db_group.command("reset")
@click.option("--env-file", default=".env", help="Environment file for database config")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def db_reset(env_file: str, force: bool):
    """Drop ALL tables and recreate schema from biz2bricks_core models.

    WARNING: This is a destructive operation that will delete all data.
    """
    import asyncio
    from pathlib import Path
    from dotenv import load_dotenv
    import os

    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        click.echo(f"Loaded environment from: {env_path}")

    db_name = os.environ.get("DATABASE_NAME", "unknown")
    db_user = os.environ.get("DATABASE_USER", "postgres")

    # Safety confirmation
    if not force:
        click.echo(
            click.style(
                "\nWARNING: This will DROP ALL TABLES and delete all data!",
                fg="red",
                bold=True,
            )
        )
        click.echo(f"Database: {db_name}")
        click.echo("")
        confirmation = click.prompt("Type 'yes' to confirm", default="no")
        if confirmation.lower() != "yes":
            click.echo("Aborted.")
            sys.exit(0)

    try:
        from sqlalchemy import text

        async def reset_database():
            # First, use raw asyncpg to drop schema and enable pgvector
            # BEFORE importing biz2bricks_core.db (which auto-creates tables)
            from google.cloud.sql.connector import Connector, IPTypes
            import asyncpg

            instance_name = os.environ.get("CLOUD_SQL_INSTANCE", "")
            db_name_env = os.environ.get("DATABASE_NAME", "doc_intelligence")
            use_connector = os.environ.get("USE_CLOUD_SQL_CONNECTOR", "true").lower() == "true"
            ip_type_str = os.environ.get("CLOUD_SQL_IP_TYPE", "PUBLIC").upper()

            click.echo("\nConnecting to database...")

            conn = None
            connector = None

            if use_connector and instance_name:
                try:
                    ip_type = IPTypes.PUBLIC if ip_type_str == "PUBLIC" else IPTypes.PRIVATE
                    loop = asyncio.get_running_loop()
                    connector = Connector(loop=loop)
                    conn = await connector.connect_async(
                        instance_name, "asyncpg",
                        user=db_user, password=os.environ.get("DATABASE_PASSWORD", ""),
                        db=db_name_env, ip_type=ip_type,
                    )
                except Exception as e:
                    click.echo(click.style(f"Cloud SQL Connector failed: {e}", fg="yellow"))

            if not conn:
                # Fallback to direct connection
                host = os.environ.get("DATABASE_HOST", "localhost")
                port = os.environ.get("DATABASE_PORT", "5432")
                conn = await asyncpg.connect(
                    host=host, port=int(port), user=db_user,
                    password=os.environ.get("DATABASE_PASSWORD", ""),
                    database=db_name_env,
                )

            click.echo(click.style("Connection successful!", fg="green"))

            try:
                # Drop and recreate schema
                click.echo("Dropping all tables (DROP SCHEMA CASCADE)...")
                await conn.execute("DROP SCHEMA public CASCADE")
                await conn.execute("CREATE SCHEMA public")
                await conn.execute(f"GRANT ALL ON SCHEMA public TO {db_user}")
                await conn.execute("GRANT ALL ON SCHEMA public TO public")
                click.echo(click.style("Schema dropped successfully!", fg="green"))

                # Enable pgvector extension BEFORE biz2bricks_core imports
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    click.echo(click.style("pgvector extension enabled", fg="green"))
                except Exception as e:
                    click.echo(click.style(f"Warning: Could not enable pgvector: {e}", fg="yellow"))
                    click.echo("  (Semantic cache will use text fallback)")

            finally:
                await conn.close()
                if connector:
                    try:
                        connector.close()
                    except Exception:
                        pass

            # NOW import and use biz2bricks_core.db - it will auto-create tables
            click.echo("Creating tables from biz2bricks_core models...")
            from biz2bricks_core import db
            # Reset the tables_created flag so it will create tables
            db._tables_created = False

            if not await db.test_connection():
                click.echo(click.style("Could not connect to database", fg="red"))
                return False

            # Tables should now be created by test_connection -> _ensure_tables
            engine = await db.get_engine_async()

            # Show created tables
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' ORDER BY table_name
                """
                    )
                )
                tables = result.fetchall()

            click.echo(click.style(f"\nTables created ({len(tables)}):", fg="green"))
            for (table_name,) in tables:
                click.echo(f"  - {table_name}")

            await db.close_all()
            return True

        success = asyncio.run(reset_database())
        if success:
            click.echo(click.style("\nDatabase reset complete!", fg="green", bold=True))
        sys.exit(0 if success else 1)

    except ImportError:
        click.echo(
            click.style("biz2bricks-core not installed. Install it first.", fg="red")
        )
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


# =============================================================================
# Commands (imported from commands module)
# =============================================================================

from biz2bricks_infra.commands.seed import seed
from biz2bricks_infra.commands.setup import setup

main.add_command(seed)
main.add_command(setup)


if __name__ == "__main__":
    main()
