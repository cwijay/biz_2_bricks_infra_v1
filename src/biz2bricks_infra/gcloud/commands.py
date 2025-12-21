"""
Core gcloud command utilities.

Shared across all provisioning operations.
"""

import json
import os
import subprocess
from typing import Tuple, Optional


def run_gcloud_command(args: list, capture_output: bool = True) -> Tuple[bool, str]:
    """
    Run a gcloud command and return success status and output.

    Args:
        args: List of arguments to pass to gcloud
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (success: bool, output: str)
    """
    cmd = ["gcloud"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() if capture_output else ""
        else:
            return False, result.stderr.strip() if capture_output else ""
    except FileNotFoundError:
        return False, "gcloud CLI not found. Please install Google Cloud SDK."
    except Exception as e:
        return False, str(e)


def check_gcloud_auth() -> bool:
    """
    Check if gcloud is authenticated with an active account.

    Returns:
        True if authenticated, False otherwise
    """
    success, output = run_gcloud_command(["auth", "list", "--format=json"])
    if not success:
        return False
    try:
        accounts = json.loads(output)
        return any(a.get("status") == "ACTIVE" for a in accounts)
    except json.JSONDecodeError:
        return False


def get_project_id() -> Optional[str]:
    """
    Get the current GCP project ID.

    First checks GCP_PROJECT_ID environment variable,
    then falls back to gcloud config.

    Returns:
        Project ID string or None if not found
    """
    # Check environment variable first
    project_id = os.environ.get("GCP_PROJECT_ID")
    if project_id:
        return project_id

    # Fall back to gcloud config
    success, output = run_gcloud_command(
        ["config", "get-value", "project", "--quiet"]
    )
    if success and output:
        return output

    return None


def run_gsutil_command(args: list, capture_output: bool = True) -> Tuple[bool, str]:
    """
    Run a gsutil command and return success status and output.

    Args:
        args: List of arguments to pass to gsutil
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (success: bool, output: str)
    """
    cmd = ["gsutil"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() if capture_output else ""
        else:
            return False, result.stderr.strip() if capture_output else ""
    except FileNotFoundError:
        return False, "gsutil not found. Please install Google Cloud SDK."
    except Exception as e:
        return False, str(e)
