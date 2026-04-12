# flux-fleet-stdlib — Shared error codes, status types, and common utilities
# for the entire FLUX fleet.

from .errors import ErrorCode, Severity, FleetError, ErrorChain, fleet_error
from .status import Status, StatusOr, status_for_error_code
from .types import AgentId, TaskId, RepoRef, Capability, FleetAddress
from .manifest import (
    AgentManifest,
    ResourceRequirements,
    OpcodeSupport,
    VALID_ROLES,
)
from .envelope import MessageEnvelope, MessageType, Priority
from .versioning import ISAVersion, OpcodeMapping

__all__ = [
    # errors
    "ErrorCode", "Severity", "FleetError", "ErrorChain", "fleet_error",
    # status
    "Status", "StatusOr", "status_for_error_code",
    # types
    "AgentId", "TaskId", "RepoRef", "Capability", "FleetAddress",
    # manifest
    "AgentManifest", "ResourceRequirements", "OpcodeSupport", "VALID_ROLES",
    # envelope
    "MessageEnvelope", "MessageType", "Priority",
    # versioning
    "ISAVersion", "OpcodeMapping",
]

__version__ = "0.2.0"
