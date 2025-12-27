"""
Subscription tier seeding commands.

Seeds default Free, Pro, and Enterprise tiers into the database.
Uses raw SQL to avoid model dependencies on doc_intelligence_ai_v3.0.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import click
from dotenv import load_dotenv


# =============================================================================
# DEFAULT TIER CONFIGURATION
# =============================================================================

# Schema matches SubscriptionTierModel from biz2bricks_core/models/usage.py:
# - tier (unique key: free, pro, enterprise)
# - display_name, description
# - monthly_token_limit
# - monthly_llamaparse_pages, monthly_file_search_queries, storage_gb_limit
# - requests_per_minute, requests_per_day, max_file_size_mb, max_concurrent_jobs
# - features (JSONB)
# - monthly_price_usd, annual_price_usd (Decimal)
# - is_active, sort_order
DEFAULT_TIERS = [
    {
        "tier": "free",
        "display_name": "Free",
        "description": "Free tier for individual users and small teams. Perfect for trying out Document Intelligence.",
        "monthly_token_limit": 50_000,
        "monthly_llamaparse_pages": 50,
        "monthly_file_search_queries": 100,
        "storage_gb_limit": Decimal("1.0"),
        "requests_per_minute": 10,
        "requests_per_day": 1000,
        "max_file_size_mb": 25,
        "max_concurrent_jobs": 2,
        "features": {
            "document_agent": True,
            "sheets_agent": True,
            "rag_search": True,
            "custom_models": False,
            "priority_support": False,
            "api_access": True,
        },
        "monthly_price_usd": Decimal("0.00"),
        "annual_price_usd": Decimal("0.00"),
        "sort_order": 1,
    },
    {
        "tier": "pro",
        "display_name": "Pro",
        "description": "Pro tier for growing teams. 10x the limits of Free with priority support.",
        "monthly_token_limit": 500_000,
        "monthly_llamaparse_pages": 500,
        "monthly_file_search_queries": 1000,
        "storage_gb_limit": Decimal("10.0"),
        "requests_per_minute": 60,
        "requests_per_day": 10000,
        "max_file_size_mb": 100,
        "max_concurrent_jobs": 10,
        "features": {
            "document_agent": True,
            "sheets_agent": True,
            "rag_search": True,
            "custom_models": True,
            "priority_support": True,
            "api_access": True,
            "advanced_analytics": True,
            "team_management": True,
        },
        "monthly_price_usd": Decimal("29.00"),
        "annual_price_usd": Decimal("290.00"),
        "sort_order": 2,
    },
    {
        "tier": "enterprise",
        "display_name": "Enterprise",
        "description": "Enterprise tier for large organizations. Custom limits available on request.",
        "monthly_token_limit": 5_000_000,
        "monthly_llamaparse_pages": 5000,
        "monthly_file_search_queries": 10000,
        "storage_gb_limit": Decimal("100.0"),
        "requests_per_minute": 300,
        "requests_per_day": 100000,
        "max_file_size_mb": 500,
        "max_concurrent_jobs": 50,
        "features": {
            "document_agent": True,
            "sheets_agent": True,
            "rag_search": True,
            "custom_models": True,
            "priority_support": True,
            "api_access": True,
            "advanced_analytics": True,
            "team_management": True,
            "sso": True,
            "audit_logs": True,
            "custom_integrations": True,
            "dedicated_support": True,
        },
        "monthly_price_usd": Decimal("199.00"),
        "annual_price_usd": Decimal("1990.00"),
        "sort_order": 3,
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================


async def get_connection():
    """Get database connection using Cloud SQL connector or direct connection."""
    instance_name = os.getenv(
        "CLOUD_SQL_INSTANCE",
        "biz2bricks-dev-v1:us-central1:biz-2-bricks-intelli-doc-dev"
    )
    target_db = os.getenv("DATABASE_NAME", "doc_intelligence")
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    use_connector = os.getenv("USE_CLOUD_SQL_CONNECTOR", "true").lower() == "true"
    ip_type_str = os.getenv("CLOUD_SQL_IP_TYPE", "PUBLIC").upper()

    if use_connector:
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
            click.echo(click.style(f"Cloud SQL Connector failed: {e}, falling back to direct connection", fg="yellow"))

    # Direct connection fallback
    import asyncpg

    db_url = os.getenv("DATABASE_URL", "")
    if db_url and "@" in db_url:
        parts = db_url.split("@")
        host_part = parts[1].split("/")[0]
        host, port = host_part.split(":") if ":" in host_part else (host_part, "5432")
    else:
        host, port = "localhost", "5432"

    conn = await asyncpg.connect(
        host=host,
        port=int(port),
        user=db_user,
        password=db_password,
        database=target_db,
    )
    return conn, None


async def close_connection(conn, connector):
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


async def list_tiers_async():
    """List existing subscription tiers."""
    conn, connector = await get_connection()
    try:
        rows = await conn.fetch("""
            SELECT id, tier, display_name, monthly_token_limit,
                   monthly_llamaparse_pages, monthly_file_search_queries,
                   storage_gb_limit, monthly_price_usd, is_active
            FROM subscription_tiers
            ORDER BY sort_order
        """)

        if not rows:
            click.echo("No subscription tiers found in database")
            return

        click.echo(click.style(f"\nSubscription Tiers ({len(rows)}):", fg="blue", bold=True))
        click.echo("-" * 90)

        for row in rows:
            status = click.style("active", fg="green") if row['is_active'] else click.style("inactive", fg="red")
            click.echo(
                f"  {row['tier']:12} | "
                f"Tokens: {row['monthly_token_limit']:>10,} | "
                f"Pages: {row['monthly_llamaparse_pages']:>5} | "
                f"Queries: {row['monthly_file_search_queries']:>6} | "
                f"Storage: {row['storage_gb_limit']:>5} GB | "
                f"${row['monthly_price_usd']}/mo | "
                f"[{status}]"
            )

    finally:
        await close_connection(conn, connector)


async def delete_all_tiers_async(force: bool = False):
    """Delete all subscription tiers."""
    conn, connector = await get_connection()
    try:
        # Check for subscriptions using these tiers
        try:
            sub_count = await conn.fetchval(
                "SELECT COUNT(*) FROM organization_subscriptions"
            )
            if sub_count > 0 and not force:
                click.echo(
                    click.style(
                        f"Warning: {sub_count} organization subscriptions exist. "
                        "Deleting tiers may affect these subscriptions.",
                        fg="yellow"
                    )
                )
                if not click.confirm("Continue?"):
                    click.echo("Operation cancelled")
                    return False
        except Exception:
            # Table might not exist yet
            pass

        await conn.execute("DELETE FROM subscription_tiers")
        click.echo(click.style("Deleted all subscription tiers", fg="green"))
        return True

    finally:
        await close_connection(conn, connector)


async def seed_tiers_async():
    """Seed default subscription tiers."""
    conn, connector = await get_connection()
    try:
        now = datetime.utcnow()

        for tier_config in DEFAULT_TIERS:
            tier_id = uuid.uuid4()

            # Check if tier already exists
            existing = await conn.fetchval(
                "SELECT id FROM subscription_tiers WHERE tier = $1",
                tier_config["tier"]
            )

            if existing:
                # Update existing tier
                await conn.execute(
                    """
                    UPDATE subscription_tiers SET
                        display_name = $2,
                        description = $3,
                        monthly_token_limit = $4,
                        monthly_llamaparse_pages = $5,
                        monthly_file_search_queries = $6,
                        storage_gb_limit = $7,
                        requests_per_minute = $8,
                        requests_per_day = $9,
                        max_file_size_mb = $10,
                        max_concurrent_jobs = $11,
                        features = $12,
                        monthly_price_usd = $13,
                        annual_price_usd = $14,
                        sort_order = $15,
                        updated_at = $16
                    WHERE tier = $1
                    """,
                    tier_config["tier"],
                    tier_config["display_name"],
                    tier_config["description"],
                    tier_config["monthly_token_limit"],
                    tier_config["monthly_llamaparse_pages"],
                    tier_config["monthly_file_search_queries"],
                    tier_config["storage_gb_limit"],
                    tier_config["requests_per_minute"],
                    tier_config["requests_per_day"],
                    tier_config["max_file_size_mb"],
                    tier_config["max_concurrent_jobs"],
                    json.dumps(tier_config["features"]),
                    tier_config["monthly_price_usd"],
                    tier_config["annual_price_usd"],
                    tier_config["sort_order"],
                    now,
                )
                click.echo(f"  Updated tier: {tier_config['tier']}")
            else:
                # Insert new tier
                await conn.execute(
                    """
                    INSERT INTO subscription_tiers (
                        id, tier, display_name, description,
                        monthly_token_limit, monthly_llamaparse_pages,
                        monthly_file_search_queries, storage_gb_limit,
                        requests_per_minute, requests_per_day,
                        max_file_size_mb, max_concurrent_jobs,
                        features, monthly_price_usd, annual_price_usd,
                        is_active, sort_order, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                              $11, $12, $13, $14, $15, $16, $17, $18, $19)
                    """,
                    tier_id,
                    tier_config["tier"],
                    tier_config["display_name"],
                    tier_config["description"],
                    tier_config["monthly_token_limit"],
                    tier_config["monthly_llamaparse_pages"],
                    tier_config["monthly_file_search_queries"],
                    tier_config["storage_gb_limit"],
                    tier_config["requests_per_minute"],
                    tier_config["requests_per_day"],
                    tier_config["max_file_size_mb"],
                    tier_config["max_concurrent_jobs"],
                    json.dumps(tier_config["features"]),
                    tier_config["monthly_price_usd"],
                    tier_config["annual_price_usd"],
                    True,  # is_active
                    tier_config["sort_order"],
                    now,
                    now,
                )
                click.echo(f"  Created tier: {tier_config['tier']}")

        click.echo(click.style("\nSuccessfully seeded subscription tiers!", fg="green"))

    finally:
        await close_connection(conn, connector)


# =============================================================================
# CLI COMMANDS
# =============================================================================


@click.group()
def seed():
    """Seed commands for database initialization."""
    pass


async def run_seed_workflow(list_only: bool, reset: bool):
    """Run the complete seed workflow in a single async context.

    This avoids multiple asyncio.run() calls which can cause
    unclosed client session warnings with Cloud SQL connectors.
    """
    if list_only:
        await list_tiers_async()
    elif reset:
        await delete_all_tiers_async(force=True)
        await seed_tiers_async()
        await list_tiers_async()
    else:
        await seed_tiers_async()
        await list_tiers_async()


@seed.command("tiers")
@click.option("--env-file", default=".env", help="Environment file for database config")
@click.option("--list", "-l", "list_only", is_flag=True, help="List current tiers without seeding")
@click.option("--reset", "-r", is_flag=True, help="Delete all tiers and re-seed")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
def seed_tiers(env_file: str, list_only: bool, reset: bool, force: bool):
    """Seed subscription tiers (Free, Pro, Enterprise).

    By default, performs an upsert (creates new tiers, updates existing ones).

    \b
    Examples:
        biz2bricks seed tiers           # Seed default tiers (upsert)
        biz2bricks seed tiers --list    # List current tiers
        biz2bricks seed tiers --reset   # Delete and re-seed tiers

    \b
    Default Tiers:
        Free       - 50,000 tokens/mo, 50 pages, 100 queries, 1 GB storage
        Pro        - 500,000 tokens/mo, 500 pages, 1,000 queries, 10 GB storage ($29/mo)
        Enterprise - 5,000,000 tokens/mo, 5,000 pages, 10,000 queries, 100 GB storage ($199/mo)
    """
    # Load environment
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        click.echo(f"Loaded environment from: {env_path}")

    target_db = os.getenv("DATABASE_NAME", "doc_intelligence")
    click.echo(f"Target database: {target_db}\n")

    # Handle confirmation for reset before entering async context
    if reset and not force:
        click.confirm(
            click.style("This will delete all tiers and re-seed. Continue?", fg="yellow"),
            abort=True
        )

    try:
        # Run all operations in single async context to avoid connector cleanup issues
        asyncio.run(run_seed_workflow(list_only, reset))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)
