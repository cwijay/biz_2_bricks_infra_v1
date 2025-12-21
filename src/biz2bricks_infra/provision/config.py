"""
Provisioning configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ProvisioningConfig:
    """Configuration for GCP resource provisioning."""

    # Project settings
    project_id: str
    region: str = "us-central1"

    # Cloud SQL
    cloud_sql_instance: str = ""
    database_name: str = "doc_intelligence"
    database_user: str = "postgres"
    database_password: str = ""
    cloud_sql_tier: str = "db-f1-micro"
    cloud_sql_availability: str = "ZONAL"  # ZONAL or REGIONAL

    # GCS
    bucket_name: str = ""
    storage_class: str = "STANDARD"

    # Service Account
    service_account_name: str = "document-intelligence-api-sa"
    service_account_roles: List[str] = field(
        default_factory=lambda: [
            "roles/cloudsql.client",
            "roles/storage.objectAdmin",
            "roles/secretmanager.secretAccessor",
        ]
    )

    # Secrets
    jwt_secret_key: str = ""
    refresh_secret_key: str = ""

    # Options
    skip_steps: List[str] = field(default_factory=list)
    dry_run: bool = False

    @classmethod
    def from_env_file(cls, env_file_path: str) -> "ProvisioningConfig":
        """Load configuration from .env file."""
        env_path = Path(env_file_path)

        if not env_path.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")

        # Parse .env file
        env_vars = {}
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes from value
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value

        # Extract required values
        project_id = env_vars.get("GCP_PROJECT_ID", "")
        if not project_id:
            raise ValueError("GCP_PROJECT_ID not found in env file")

        # Parse CLOUD_SQL_INSTANCE (format: project:region:instance)
        cloud_sql_instance_full = env_vars.get("CLOUD_SQL_INSTANCE", "")
        region = "us-central1"
        cloud_sql_instance = ""

        if cloud_sql_instance_full:
            parts = cloud_sql_instance_full.split(":")
            if len(parts) == 3:
                region = parts[1]
                cloud_sql_instance = parts[2]

        return cls(
            project_id=project_id,
            region=region,
            cloud_sql_instance=cloud_sql_instance,
            database_name=env_vars.get("DATABASE_NAME", "doc_intelligence"),
            database_user=env_vars.get("DATABASE_USER", "postgres"),
            database_password=env_vars.get("DATABASE_PASSWORD", ""),
            bucket_name=env_vars.get("GCS_BUCKET_NAME", ""),
            jwt_secret_key=env_vars.get("JWT_SECRET_KEY", ""),
            refresh_secret_key=env_vars.get("REFRESH_SECRET_KEY", ""),
        )
