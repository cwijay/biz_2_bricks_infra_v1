"""
GCP resource provisioner.

Orchestrates provisioning of all GCP resources:
- Cloud SQL PostgreSQL instance
- GCS bucket
- Service Account with IAM roles
- Secret Manager secrets
"""

import json
import secrets
import string
from typing import Optional

from biz2bricks_infra.gcloud.commands import (
    run_gcloud_command,
    run_gsutil_command,
    check_gcloud_auth,
    get_project_id,
)
from biz2bricks_infra.provision.config import ProvisioningConfig


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def colored(text: str, color: str) -> str:
    """Return colored text."""
    return f"{color}{text}{Colors.END}"


def generate_password(length: int = 32) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Provisioner:
    """Orchestrates GCP resource provisioning."""

    def __init__(self, env_file: str = ".env.production", dry_run: bool = False):
        self.dry_run = dry_run
        self.config: Optional[ProvisioningConfig] = None

        try:
            self.config = ProvisioningConfig.from_env_file(env_file)
            self.config.dry_run = dry_run
        except FileNotFoundError as e:
            print(colored(f"Error: {e}", Colors.RED))
        except ValueError as e:
            print(colored(f"Error: {e}", Colors.RED))

    def check_prerequisites(self) -> bool:
        """Check that all prerequisites are met."""
        print(colored("\n=== Checking Prerequisites ===", Colors.BOLD))

        # Check gcloud auth
        if not check_gcloud_auth():
            print(colored("  gcloud not authenticated. Run: gcloud auth login", Colors.RED))
            return False
        print(colored("  gcloud authenticated ✓", Colors.GREEN))

        # Check config loaded
        if not self.config:
            print(colored("  Configuration not loaded ✗", Colors.RED))
            return False
        print(colored("  Configuration loaded ✓", Colors.GREEN))

        # Check project ID
        project_id = get_project_id()
        if not project_id:
            print(colored("  GCP project ID not found ✗", Colors.RED))
            return False
        print(colored(f"  Project: {project_id} ✓", Colors.GREEN))

        return True

    def provision_all(self) -> bool:
        """Provision all GCP resources."""
        if not self.config:
            return False

        print(colored("\n=== Provisioning GCP Resources ===", Colors.BOLD))

        success = True
        success = self.provision_cloud_sql() and success
        success = self.provision_gcs_bucket() and success
        success = self.provision_service_account() and success
        success = self.provision_secrets() and success

        if success:
            print(colored("\n=== All resources provisioned successfully! ===", Colors.GREEN))
        else:
            print(colored("\n=== Some resources failed to provision ===", Colors.RED))

        return success

    def provision_cloud_sql(self) -> bool:
        """Provision Cloud SQL PostgreSQL instance."""
        if not self.config:
            return False

        print(colored("\n--- Cloud SQL ---", Colors.BLUE))

        instance = self.config.cloud_sql_instance
        project = self.config.project_id
        region = self.config.region

        # Check if instance exists
        success, output = run_gcloud_command([
            "sql", "instances", "describe", instance,
            "--project", project,
            "--format=json",
        ])

        if success:
            print(colored(f"  Instance {instance} already exists ✓", Colors.GREEN))
        else:
            # Create instance
            print(f"  Creating instance {instance}...")

            if self.dry_run:
                print(colored("  [DRY RUN] Would create Cloud SQL instance", Colors.YELLOW))
                return True

            success, output = run_gcloud_command([
                "sql", "instances", "create", instance,
                "--project", project,
                "--region", region,
                "--database-version", "POSTGRES_15",
                "--tier", self.config.cloud_sql_tier,
                "--storage-type", "SSD",
                "--storage-size", "10GB",
                "--storage-auto-increase",
                "--availability-type", self.config.cloud_sql_availability,
                "--no-backup",  # Can be enabled later
            ])

            if not success:
                print(colored(f"  Failed to create instance: {output}", Colors.RED))
                return False
            print(colored(f"  Instance {instance} created ✓", Colors.GREEN))

        # Create database
        db_name = self.config.database_name
        success, output = run_gcloud_command([
            "sql", "databases", "describe", db_name,
            "--instance", instance,
            "--project", project,
        ])

        if success:
            print(colored(f"  Database {db_name} already exists ✓", Colors.GREEN))
        else:
            if self.dry_run:
                print(colored(f"  [DRY RUN] Would create database {db_name}", Colors.YELLOW))
            else:
                success, output = run_gcloud_command([
                    "sql", "databases", "create", db_name,
                    "--instance", instance,
                    "--project", project,
                ])
                if success:
                    print(colored(f"  Database {db_name} created ✓", Colors.GREEN))
                else:
                    print(colored(f"  Failed to create database: {output}", Colors.RED))

        # Set user password
        if self.config.database_password:
            if self.dry_run:
                print(colored("  [DRY RUN] Would set database password", Colors.YELLOW))
            else:
                success, output = run_gcloud_command([
                    "sql", "users", "set-password", self.config.database_user,
                    "--instance", instance,
                    "--project", project,
                    "--password", self.config.database_password,
                ])
                if success:
                    print(colored("  Database password set ✓", Colors.GREEN))
                else:
                    print(colored(f"  Failed to set password: {output}", Colors.RED))

        return True

    def provision_gcs_bucket(self) -> bool:
        """Provision GCS bucket."""
        if not self.config or not self.config.bucket_name:
            print(colored("  No bucket name configured, skipping", Colors.YELLOW))
            return True

        print(colored("\n--- GCS Bucket ---", Colors.BLUE))

        bucket = self.config.bucket_name
        location = self.config.region

        # Check if bucket exists
        success, output = run_gsutil_command(["ls", "-b", f"gs://{bucket}"])

        if success:
            print(colored(f"  Bucket {bucket} already exists ✓", Colors.GREEN))
            return True

        if self.dry_run:
            print(colored(f"  [DRY RUN] Would create bucket {bucket}", Colors.YELLOW))
            return True

        # Create bucket
        success, output = run_gsutil_command([
            "mb",
            "-l", location,
            "-c", self.config.storage_class,
            f"gs://{bucket}",
        ])

        if not success:
            print(colored(f"  Failed to create bucket: {output}", Colors.RED))
            return False

        print(colored(f"  Bucket {bucket} created ✓", Colors.GREEN))

        # Enable versioning
        run_gsutil_command(["versioning", "set", "on", f"gs://{bucket}"])
        print(colored("  Versioning enabled ✓", Colors.GREEN))

        # Enable uniform bucket-level access
        run_gsutil_command(["uniformbucketlevelaccess", "set", "on", f"gs://{bucket}"])
        print(colored("  Uniform bucket-level access enabled ✓", Colors.GREEN))

        return True

    def provision_service_account(self) -> bool:
        """Provision service account with IAM roles."""
        if not self.config:
            return False

        print(colored("\n--- Service Account ---", Colors.BLUE))

        sa_name = self.config.service_account_name
        project = self.config.project_id
        sa_email = f"{sa_name}@{project}.iam.gserviceaccount.com"

        # Check if SA exists
        success, output = run_gcloud_command([
            "iam", "service-accounts", "describe", sa_email,
            "--project", project,
        ])

        if success:
            print(colored(f"  Service account {sa_name} already exists ✓", Colors.GREEN))
        else:
            if self.dry_run:
                print(colored(f"  [DRY RUN] Would create service account {sa_name}", Colors.YELLOW))
            else:
                success, output = run_gcloud_command([
                    "iam", "service-accounts", "create", sa_name,
                    "--project", project,
                    "--display-name", "Document Intelligence API",
                ])
                if success:
                    print(colored(f"  Service account {sa_name} created ✓", Colors.GREEN))
                else:
                    print(colored(f"  Failed to create SA: {output}", Colors.RED))
                    return False

        # Assign roles
        for role in self.config.service_account_roles:
            if self.dry_run:
                print(colored(f"  [DRY RUN] Would assign role {role}", Colors.YELLOW))
            else:
                success, output = run_gcloud_command([
                    "projects", "add-iam-policy-binding", project,
                    "--member", f"serviceAccount:{sa_email}",
                    "--role", role,
                    "--condition=None",
                ])
                if success:
                    print(colored(f"  Role {role} assigned ✓", Colors.GREEN))
                else:
                    # Role might already be assigned
                    print(colored(f"  Role {role} (may already be assigned)", Colors.YELLOW))

        return True

    def provision_secrets(self) -> bool:
        """Provision Secret Manager secrets."""
        if not self.config:
            return False

        print(colored("\n--- Secret Manager ---", Colors.BLUE))

        secrets_to_create = [
            ("DATABASE_PASSWORD", self.config.database_password or generate_password()),
            ("JWT_SECRET_KEY", self.config.jwt_secret_key or generate_password(64)),
            ("REFRESH_SECRET_KEY", self.config.refresh_secret_key or generate_password(64)),
        ]

        for secret_name, secret_value in secrets_to_create:
            self._create_secret(secret_name, secret_value)

        return True

    def _create_secret(self, name: str, value: str) -> bool:
        """Create or update a secret in Secret Manager."""
        project = self.config.project_id

        # Check if secret exists
        success, output = run_gcloud_command([
            "secrets", "describe", name,
            "--project", project,
        ])

        if success:
            print(colored(f"  Secret {name} already exists ✓", Colors.GREEN))
            return True

        if self.dry_run:
            print(colored(f"  [DRY RUN] Would create secret {name}", Colors.YELLOW))
            return True

        # Create secret
        success, output = run_gcloud_command([
            "secrets", "create", name,
            "--project", project,
            "--replication-policy", "automatic",
        ])

        if not success:
            print(colored(f"  Failed to create secret {name}: {output}", Colors.RED))
            return False

        # Add secret version
        import subprocess

        cmd = [
            "gcloud", "secrets", "versions", "add", name,
            "--project", project,
            "--data-file=-",
        ]
        result = subprocess.run(
            cmd,
            input=value.encode(),
            capture_output=True,
        )

        if result.returncode == 0:
            print(colored(f"  Secret {name} created ✓", Colors.GREEN))
            return True
        else:
            print(colored(f"  Failed to add secret value: {result.stderr.decode()}", Colors.RED))
            return False

    # =========================================================================
    # Status Methods
    # =========================================================================

    def show_status(self):
        """Show status of all provisioned GCP resources."""
        if not self.config:
            print(colored("Configuration not loaded", Colors.RED))
            return

        print(colored("\n=== GCP Resource Status ===", Colors.BOLD))

        self._show_cloud_sql_status()
        self._show_gcs_bucket_status()
        self._show_service_account_status()
        self._show_secrets_status()

    def _show_cloud_sql_status(self):
        """Show Cloud SQL instance status."""
        print(colored("\n--- Cloud SQL ---", Colors.BLUE))

        instance = self.config.cloud_sql_instance
        project = self.config.project_id

        success, output = run_gcloud_command([
            "sql", "instances", "describe", instance,
            "--project", project,
            "--format=json",
        ])

        if success:
            import json
            try:
                data = json.loads(output)
                state = data.get("state", "UNKNOWN")
                region = data.get("region", "")
                tier = data.get("settings", {}).get("tier", "")
                ip = data.get("ipAddresses", [{}])[0].get("ipAddress", "N/A")
                print(colored(f"  Instance: {instance} - {state}", Colors.GREEN))
                print(f"    Region: {region}, Tier: {tier}")
                print(f"    IP: {ip}")
            except json.JSONDecodeError:
                print(colored(f"  Instance: {instance} - EXISTS", Colors.GREEN))
        else:
            print(colored(f"  Instance: {instance} - NOT FOUND", Colors.YELLOW))

    def _show_gcs_bucket_status(self):
        """Show GCS bucket status."""
        print(colored("\n--- GCS Bucket ---", Colors.BLUE))

        bucket = self.config.bucket_name
        if not bucket:
            print(colored("  No bucket configured", Colors.YELLOW))
            return

        success, output = run_gsutil_command(["ls", "-b", f"gs://{bucket}"])

        if success:
            print(colored(f"  Bucket: {bucket} - EXISTS", Colors.GREEN))

            # Get versioning status
            success, version_output = run_gsutil_command(["versioning", "get", f"gs://{bucket}"])
            if success and "Enabled" in version_output:
                print("    Versioning: Enabled")
            else:
                print("    Versioning: Disabled")
        else:
            print(colored(f"  Bucket: {bucket} - NOT FOUND", Colors.YELLOW))

    def _show_service_account_status(self):
        """Show service account status."""
        print(colored("\n--- Service Account ---", Colors.BLUE))

        sa_name = self.config.service_account_name
        project = self.config.project_id
        sa_email = f"{sa_name}@{project}.iam.gserviceaccount.com"

        success, output = run_gcloud_command([
            "iam", "service-accounts", "describe", sa_email,
            "--project", project,
            "--format=json",
        ])

        if success:
            print(colored(f"  Service Account: {sa_name} - EXISTS", Colors.GREEN))
            print(f"    Email: {sa_email}")

            # List assigned roles
            success, roles_output = run_gcloud_command([
                "projects", "get-iam-policy", project,
                "--flatten=bindings[].members",
                "--filter", f"bindings.members:serviceAccount:{sa_email}",
                "--format=value(bindings.role)",
            ])

            if success and roles_output.strip():
                print("    Roles:")
                for role in roles_output.strip().split("\n"):
                    print(f"      - {role}")
        else:
            print(colored(f"  Service Account: {sa_name} - NOT FOUND", Colors.YELLOW))

    def _show_secrets_status(self):
        """Show Secret Manager secrets status."""
        print(colored("\n--- Secret Manager ---", Colors.BLUE))

        project = self.config.project_id
        secrets_to_check = ["DATABASE_PASSWORD", "JWT_SECRET_KEY", "REFRESH_SECRET_KEY"]

        for secret_name in secrets_to_check:
            success, output = run_gcloud_command([
                "secrets", "describe", secret_name,
                "--project", project,
            ])

            if success:
                print(colored(f"  {secret_name} - EXISTS", Colors.GREEN))
            else:
                print(colored(f"  {secret_name} - NOT FOUND", Colors.YELLOW))

    # =========================================================================
    # Delete Methods
    # =========================================================================

    def delete_all(self) -> bool:
        """Delete all provisioned GCP resources."""
        if not self.config:
            return False

        print(colored("\n=== Deleting ALL GCP Resources ===", Colors.BOLD))

        success = True
        # Delete in reverse order of dependencies
        success = self.delete_secrets() and success
        success = self.delete_service_account() and success
        success = self.delete_gcs_bucket() and success
        success = self.delete_cloud_sql() and success

        if success:
            print(colored("\n=== All resources deleted ===", Colors.GREEN))
        else:
            print(colored("\n=== Some deletions failed ===", Colors.RED))

        return success

    def delete_cloud_sql(self) -> bool:
        """Delete Cloud SQL instance."""
        if not self.config:
            return False

        print(colored("\n--- Deleting Cloud SQL ---", Colors.BLUE))

        instance = self.config.cloud_sql_instance
        project = self.config.project_id

        success, output = run_gcloud_command([
            "sql", "instances", "delete", instance,
            "--project", project,
            "--quiet",
        ])

        if success:
            print(colored(f"  Instance {instance} deleted ✓", Colors.GREEN))
            return True
        else:
            if "not found" in output.lower() or "does not exist" in output.lower():
                print(colored(f"  Instance {instance} does not exist", Colors.YELLOW))
                return True
            print(colored(f"  Failed to delete instance: {output}", Colors.RED))
            return False

    def delete_gcs_bucket(self) -> bool:
        """Delete GCS bucket and all contents."""
        if not self.config or not self.config.bucket_name:
            return True

        print(colored("\n--- Deleting GCS Bucket ---", Colors.BLUE))

        bucket = self.config.bucket_name

        # Delete all objects first
        success, output = run_gsutil_command(["-m", "rm", "-r", f"gs://{bucket}/**"])
        # Ignore errors if bucket is empty

        # Delete bucket
        success, output = run_gsutil_command(["rb", f"gs://{bucket}"])

        if success:
            print(colored(f"  Bucket {bucket} deleted ✓", Colors.GREEN))
            return True
        else:
            if "not found" in output.lower() or "does not exist" in output.lower():
                print(colored(f"  Bucket {bucket} does not exist", Colors.YELLOW))
                return True
            print(colored(f"  Failed to delete bucket: {output}", Colors.RED))
            return False

    def delete_service_account(self) -> bool:
        """Delete service account."""
        if not self.config:
            return False

        print(colored("\n--- Deleting Service Account ---", Colors.BLUE))

        sa_name = self.config.service_account_name
        project = self.config.project_id
        sa_email = f"{sa_name}@{project}.iam.gserviceaccount.com"

        success, output = run_gcloud_command([
            "iam", "service-accounts", "delete", sa_email,
            "--project", project,
            "--quiet",
        ])

        if success:
            print(colored(f"  Service account {sa_name} deleted ✓", Colors.GREEN))
            return True
        else:
            if "not found" in output.lower() or "does not exist" in output.lower():
                print(colored(f"  Service account {sa_name} does not exist", Colors.YELLOW))
                return True
            print(colored(f"  Failed to delete service account: {output}", Colors.RED))
            return False

    def delete_secrets(self) -> bool:
        """Delete all Secret Manager secrets."""
        if not self.config:
            return False

        print(colored("\n--- Deleting Secrets ---", Colors.BLUE))

        project = self.config.project_id
        secrets_to_delete = ["DATABASE_PASSWORD", "JWT_SECRET_KEY", "REFRESH_SECRET_KEY"]

        all_success = True
        for secret_name in secrets_to_delete:
            success, output = run_gcloud_command([
                "secrets", "delete", secret_name,
                "--project", project,
                "--quiet",
            ])

            if success:
                print(colored(f"  {secret_name} deleted ✓", Colors.GREEN))
            else:
                if "not found" in output.lower():
                    print(colored(f"  {secret_name} does not exist", Colors.YELLOW))
                else:
                    print(colored(f"  Failed to delete {secret_name}: {output}", Colors.RED))
                    all_success = False

        return all_success
