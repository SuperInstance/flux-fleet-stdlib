# flux-fleet-stdlib — Shared error codes, status types, and common utilities
# for the entire FLUX fleet.

from .errors import ErrorCode, Severity, FleetError, ErrorChain, fleet_error
from .status import Status, StatusOr
from .types import AgentId, TaskId, RepoRef, Capability, FleetAddress

__all__ = [
    # errors
    "ErrorCode", "Severity", "FleetError", "ErrorChain", "fleet_error",
    # status
    "Status", "StatusOr",
    # types
    "AgentId", "TaskId", "RepoRef", "Capability", "FleetAddress",
]

__version__ = "0.1.0"
