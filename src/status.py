"""
flux-fleet-stdlib / status.py
Unified status codes for cooperative fleet operations.

Provides a ``Status`` enum (the "why") and a ``StatusOr<T>`` wrapper (the
"what") modelled after Google's StatusOr / Rust's Result so that every repo
can return structured outcomes instead of ad-hoc tuples.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

class Status(str, enum.Enum):
    """Canonical fleet status codes."""

    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    TIMEOUT = "TIMEOUT"
    REFUSED = "REFUSED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"
    RATE_LIMITED = "RATE_LIMITED"


# String constants matching the enum (for cross-language parity).
STATUS_SUCCESS = "SUCCESS"
STATUS_PENDING = "PENDING"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_REFUSED = "REFUSED"
STATUS_ERROR = "ERROR"
STATUS_CANCELLED = "CANCELLED"
STATUS_PARTIAL = "PARTIAL"
STATUS_RATE_LIMITED = "RATE_LIMITED"

ALL_STATUSES = frozenset(s.value for s in Status)

# Map some error codes ↔ statuses for convenience.
_ERROR_TO_STATUS = {
    "VM_HALTED": Status.ERROR,
    "VM_CYCLE_LIMIT": Status.ERROR,
    "VM_DIV_ZERO": Status.ERROR,
    "VM_STACK_OVERFLOW": Status.ERROR,
    "VM_STACK_UNDERFLOW": Status.ERROR,
    "VM_INVALID_OPCODE": Status.ERROR,
    "VM_TYPE_ERROR": Status.ERROR,
    "VM_RESOURCE_ERROR": Status.ERROR,
    "VM_OUT_OF_MEMORY": Status.ERROR,
    "VM_UNKNOWN_INSTRUCTION": Status.ERROR,
    "COOP_TIMEOUT": Status.TIMEOUT,
    "COOP_NO_CAPABLE_AGENT": Status.REFUSED,
    "COOP_TRANSPORT_FAILURE": Status.ERROR,
    "COOP_TASK_EXPIRED": Status.TIMEOUT,
    "COOP_AGENT_REFUSED": Status.REFUSED,
    "COOP_UNKNOWN_REQUEST": Status.ERROR,
    "COOP_DUPLICATE_TASK": Status.ERROR,
    "COOP_INVALID_PARAMS": Status.REFUSED,
    "COOP_DESERIALIZATION_ERROR": Status.ERROR,
    "TRANSPORT_GIT_ERROR": Status.ERROR,
    "TRANSPORT_PUSH_FAILED": Status.ERROR,
    "TRANSPORT_PULL_FAILED": Status.ERROR,
    "TRANSPORT_MERGE_CONFLICT": Status.PARTIAL,
    "TRANSPORT_AUTH_FAILURE": Status.REFUSED,
    "TRANSPORT_REPO_NOT_FOUND": Status.ERROR,
    "TRANSPORT_RATE_LIMITED": Status.RATE_LIMITED,
    "TRANSPORT_NETWORK_ERROR": Status.ERROR,
    "TRUST_SCORE_LOW": Status.REFUSED,
    "TRUST_POISONING": Status.ERROR,
    "TRUST_UNKNOWN_AGENT": Status.REFUSED,
    "TRUST_ATTESTATION_FAILED": Status.ERROR,
    "SPEC_OPCODE_CONFLICT": Status.ERROR,
    "SPEC_FORMAT_VIOLATION": Status.ERROR,
    "SPEC_ENCODING_ERROR": Status.ERROR,
    "SPEC_MISSING_HANDLER": Status.ERROR,
    "SPEC_VERSION_MISMATCH": Status.ERROR,
    "SPEC_UNKNOWN_OPCODE": Status.ERROR,
    "SECURITY_CAP_REQUIRED": Status.REFUSED,
    "SECURITY_CAP_DENIED": Status.REFUSED,
    "SECURITY_SANDBOX_VIOLATION": Status.ERROR,
    "SECURITY_UNVERIFIED_BYTECODE": Status.REFUSED,
}


def status_for_error_code(code: str) -> Status:
    """Derive a ``Status`` from a fleet error code."""
    return _ERROR_TO_STATUS.get(code, Status.ERROR)


# ---------------------------------------------------------------------------
# StatusOr<T>
# ---------------------------------------------------------------------------

@dataclass
class StatusOr(Generic[T]):
    """Either a successful value or a status+error description.

    Modelled after ``absl::StatusOr`` / Rust ``Result``.

    Usage::

        result = StatusOr(value=42)
        assert result.ok()
        assert result.value == 42

        result = StatusOr(status=Status.REFUSED, error_message="nope")
        assert not result.ok()
    """

    # Exactly one branch is populated.
    _value: Optional[T] = field(default=None, repr=False)
    _status: Status = field(default=Status.ERROR)
    _error_message: str = ""
    _error_code: str = ""

    def __init__(
        self,
        *,
        value: Optional[T] = None,
        status: Optional[Status] = None,
        error_message: str = "",
        error_code: str = "",
    ):
        # Normalize: value wins when provided.
        if value is not None:
            object.__setattr__(self, "_value", value)
            object.__setattr__(self, "_status", Status.SUCCESS)
            object.__setattr__(self, "_error_message", "")
            object.__setattr__(self, "_error_code", "")
        else:
            object.__setattr__(self, "_value", None)
            object.__setattr__(self, "_status", status if status is not None else Status.ERROR)
            object.__setattr__(self, "_error_message", error_message)
            object.__setattr__(self, "_error_code", error_code)

    # -- public API ---------------------------------------------------------

    def ok(self) -> bool:
        return self._status == Status.SUCCESS

    @property
    def status(self) -> Status:
        return self._status

    @property
    def value(self) -> T:  # type: ignore[valid-type]
        if not self.ok():
            raise ValueError(
                f"StatusOr is not OK: {self._status.value} – {self._error_message}"
            )
        return self._value  # type: ignore[return-value]

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def error_code(self) -> str:
        return self._error_code

    def __bool__(self) -> bool:
        return self.ok()

    def __str__(self) -> str:
        if self.ok():
            return f"StatusOr(OK, value={self._value!r})"
        return f"StatusOr({self._status.value}, code={self._error_code!r}, msg={self._error_message!r})"

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        if self.ok():
            return {"status": self._status.value, "value": self._value}
        return {
            "status": self._status.value,
            "error_code": self._error_code,
            "error_message": self._error_message,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StatusOr[Any]":
        if d.get("status") == Status.SUCCESS.value and "value" in d:
            return cls(value=d["value"])
        return cls(
            status=Status(d.get("status", "ERROR")),
            error_message=d.get("error_message", ""),
            error_code=d.get("error_code", ""),
        )
