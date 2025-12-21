"""
GCP resource provisioning.
"""

from biz2bricks_infra.provision.provisioner import Provisioner
from biz2bricks_infra.provision.config import ProvisioningConfig

__all__ = [
    "Provisioner",
    "ProvisioningConfig",
]
