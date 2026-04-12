"""
flux-fleet-stdlib / errors.py
Unified error code registry for the entire FLUX fleet.

Every repo in the fleet should import from this module (or its Go equivalent)
so that error codes share a single taxonomy.  Codes are plain strings chosen
to be valid Go const identifiers and also natural to use in Python / Rust.

Domain layout
─────────────
  VM         – virtual-machine execution errors
  COOP       – cooperative / inter-agent coordination errors
  TRANSPORT  – git-based message-passing errors
  TRUST      – trust-score and reputation errors
  SPEC       – specification / bytecode format errors
  SECURITY   – capability and sandbox violations
"""

from __future__ import annotations

import enum
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Error-code enum
# ---------------------------------------------------------------------------

class ErrorCode(str, enum.Enum):
    """Canonical fleet error codes.

    The *value* of each member is the string constant that cross-language
    consumers (Go, Rust, …) will compare against.  Treat these as immutable.
    """

    # ── VM domain ────────────────────────────────────────────────────────
    VM_HALTED = "VM_HALTED"
    VM_CYCLE_LIMIT = "VM_CYCLE_LIMIT"
    VM_DIV_ZERO = "VM_DIV_ZERO"
    VM_STACK_OVERFLOW = "VM_STACK_OVERFLOW"
    VM_STACK_UNDERFLOW = "VM_STACK_UNDERFLOW"
    VM_INVALID_OPCODE = "VM_INVALID_OPCODE"
    VM_TYPE_ERROR = "VM_TYPE_ERROR"
    VM_RESOURCE_ERROR = "VM_RESOURCE_ERROR"
    VM_OUT_OF_MEMORY = "VM_OUT_OF_MEMORY"
    VM_UNKNOWN_INSTRUCTION = "VM_UNKNOWN_INSTRUCTION"

    # ── COOP domain ──────────────────────────────────────────────────────
    COOP_TIMEOUT = "COOP_TIMEOUT"
    COOP_NO_CAPABLE_AGENT = "COOP_NO_CAPABLE_AGENT"
    COOP_TRANSPORT_FAILURE = "COOP_TRANSPORT_FAILURE"
    COOP_TASK_EXPIRED = "COOP_TASK_EXPIRED"
    COOP_AGENT_REFUSED = "COOP_AGENT_REFUSED"
    COOP_UNKNOWN_REQUEST = "COOP_UNKNOWN_REQUEST"
    COOP_DUPLICATE_TASK = "COOP_DUPLICATE_TASK"
    COOP_INVALID_PARAMS = "COOP_INVALID_PARAMS"
    COOP_DESERIALIZATION_ERROR = "COOP_DESERIALIZATION_ERROR"

    # ── TRANSPORT domain ─────────────────────────────────────────────────
    TRANSPORT_GIT_ERROR = "TRANSPORT_GIT_ERROR"
    TRANSPORT_PUSH_FAILED = "TRANSPORT_PUSH_FAILED"
    TRANSPORT_PULL_FAILED = "TRANSPORT_PULL_FAILED"
    TRANSPORT_MERGE_CONFLICT = "TRANSPORT_MERGE_CONFLICT"
    TRANSPORT_AUTH_FAILURE = "TRANSPORT_AUTH_FAILURE"
    TRANSPORT_REPO_NOT_FOUND = "TRANSPORT_REPO_NOT_FOUND"
    TRANSPORT_RATE_LIMITED = "TRANSPORT_RATE_LIMITED"
    TRANSPORT_NETWORK_ERROR = "TRANSPORT_NETWORK_ERROR"

    # ── TRUST domain ─────────────────────────────────────────────────────
    TRUST_SCORE_LOW = "TRUST_SCORE_LOW"
    TRUST_POISONING = "TRUST_POISONING"
    TRUST_UNKNOWN_AGENT = "TRUST_UNKNOWN_AGENT"
    TRUST_ATTESTATION_FAILED = "TRUST_ATTESTATION_FAILED"

    # ── SPEC domain ──────────────────────────────────────────────────────
    SPEC_OPCODE_CONFLICT = "SPEC_OPCODE_CONFLICT"
    SPEC_FORMAT_VIOLATION = "SPEC_FORMAT_VIOLATION"
    SPEC_ENCODING_ERROR = "SPEC_ENCODING_ERROR"
    SPEC_MISSING_HANDLER = "SPEC_MISSING_HANDLER"
    SPEC_VERSION_MISMATCH = "SPEC_VERSION_MISMATCH"
    SPEC_UNKNOWN_OPCODE = "SPEC_UNKNOWN_OPCODE"

    # ── SECURITY domain ──────────────────────────────────────────────────
    SECURITY_CAP_REQUIRED = "SECURITY_CAP_REQUIRED"
    SECURITY_CAP_DENIED = "SECURITY_CAP_DENIED"
    SECURITY_SANDBOX_VIOLATION = "SECURITY_SANDBOX_VIOLATION"
    SECURITY_UNVERIFIED_BYTECODE = "SECURITY_UNVERIFIED_BYTECODE"


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity(str, enum.Enum):
    """How bad is it?"""
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# FleetError – the canonical exception class
# ---------------------------------------------------------------------------

@dataclass
class FleetError(Exception):
    """Rich error that every fleet repo can create and every fleet repo can
    understand.

    Carries the standard fields plus an arbitrary ``context`` dict for
    domain-specific metadata.
    """

    code: str
    message: str
    severity: str = Severity.ERROR.value
    source_repo: str = ""
    source_agent: str = ""
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # Allow dataclass fields plus Exception positional args to coexist.
    def __init__(
        self,
        code: str,
        message: str,
        severity: str = Severity.ERROR.value,
        source_repo: str = "",
        source_agent: str = "",
        timestamp: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        error_id: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.severity = severity
        self.source_repo = source_repo
        self.source_agent = source_agent
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.context = context if context is not None else {}
        self.error_id = error_id if error_id is not None else uuid.uuid4().hex[:12]
        # Exception base needs the message string
        super().__init__(f"[{code}] {message}")

    # -- convenience helpers -------------------------------------------------

    def __str__(self) -> str:
        repo = f" ({self.source_repo})" if self.source_repo else ""
        agent = f" agent={self.source_agent}" if self.source_agent else ""
        return f"[{self.code}]{repo}{agent} {self.message}"

    def __repr__(self) -> str:
        return (
            f"FleetError(code={self.code!r}, message={self.message!r}, "
            f"severity={self.severity!r}, source_repo={self.source_repo!r}, "
            f"source_agent={self.source_agent!r})"
        )

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "source_repo": self.source_repo,
            "source_agent": self.source_agent,
            "timestamp": self.timestamp,
            "error_id": self.error_id,
            "context": self.context,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FleetError":
        return cls(**{
            k: d[k] for k in (
                "code", "message", "severity", "source_repo",
                "source_agent", "timestamp", "context", "error_id",
            ) if k in d
        })

    @classmethod
    def from_json(cls, s: str) -> "FleetError":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# ErrorChain – wrapped / nested errors
# ---------------------------------------------------------------------------

@dataclass
class ErrorChain:
    """Ordered chain of errors from innermost (root cause) to outermost.

    Useful for wrapping lower-level errors with higher-level context while
    preserving the full causal history.
    """

    errors: List[FleetError] = field(default_factory=list)

    def wrap(self, err: FleetError) -> "ErrorChain":
        """Add *err* as the outermost (most recent) layer."""
        self.errors.append(err)
        return self

    def root(self) -> Optional[FleetError]:
        """Return the innermost (first) error, or ``None``."""
        return self.errors[0] if self.errors else None

    def outermost(self) -> Optional[FleetError]:
        """Return the last (most recent) error, or ``None``."""
        return self.errors[-1] if self.errors else None

    def __len__(self) -> int:
        return len(self.errors)

    def __bool__(self) -> bool:
        return len(self.errors) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {"errors": [e.to_dict() for e in self.errors]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ErrorChain":
        return cls(errors=[FleetError.from_dict(e) for e in d.get("errors", [])])

    @classmethod
    def from_json(cls, s: str) -> "ErrorChain":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def fleet_error(
    code: str,
    message: str,
    severity: str = Severity.ERROR.value,
    source_repo: str = "",
    source_agent: str = "",
    **context: Any,
) -> FleetError:
    """Quick factory – the preferred way to create errors in fleet code.

    Usage::

        from .errors import fleet_error, ErrorCode

        raise fleet_error(
            ErrorCode.VM_CYCLE_LIMIT.value,
            "Agent exceeded 10_000 cycles",
            source_repo="flux-coop-runtime",
            source_agent="executor-01",
            cycle_count=10_247,
        )
    """
    return FleetError(
        code=code,
        message=message,
        severity=severity,
        source_repo=source_repo,
        source_agent=source_agent,
        context=context,
    )


# ---------------------------------------------------------------------------
# Standalone string constants (for fast access / static analysis)
# ---------------------------------------------------------------------------
# These mirror the enum values so Go / Rust consumers can literally
# copy-paste the same strings.

ERR_VM_HALTED = "VM_HALTED"
ERR_VM_CYCLE_LIMIT = "VM_CYCLE_LIMIT"
ERR_VM_DIV_ZERO = "VM_DIV_ZERO"
ERR_VM_STACK_OVERFLOW = "VM_STACK_OVERFLOW"
ERR_VM_STACK_UNDERFLOW = "VM_STACK_UNDERFLOW"
ERR_VM_INVALID_OPCODE = "VM_INVALID_OPCODE"
ERR_VM_TYPE_ERROR = "VM_TYPE_ERROR"
ERR_VM_RESOURCE_ERROR = "VM_RESOURCE_ERROR"
ERR_VM_OUT_OF_MEMORY = "VM_OUT_OF_MEMORY"
ERR_VM_UNKNOWN_INSTRUCTION = "VM_UNKNOWN_INSTRUCTION"

ERR_COOP_TIMEOUT = "COOP_TIMEOUT"
ERR_COOP_NO_CAPABLE_AGENT = "COOP_NO_CAPABLE_AGENT"
ERR_COOP_TRANSPORT_FAILURE = "COOP_TRANSPORT_FAILURE"
ERR_COOP_TASK_EXPIRED = "COOP_TASK_EXPIRED"
ERR_COOP_AGENT_REFUSED = "COOP_AGENT_REFUSED"
ERR_COOP_UNKNOWN_REQUEST = "COOP_UNKNOWN_REQUEST"
ERR_COOP_DUPLICATE_TASK = "COOP_DUPLICATE_TASK"
ERR_COOP_INVALID_PARAMS = "COOP_INVALID_PARAMS"
ERR_COOP_DESERIALIZATION_ERROR = "COOP_DESERIALIZATION_ERROR"

ERR_TRANSPORT_GIT_ERROR = "TRANSPORT_GIT_ERROR"
ERR_TRANSPORT_PUSH_FAILED = "TRANSPORT_PUSH_FAILED"
ERR_TRANSPORT_PULL_FAILED = "TRANSPORT_PULL_FAILED"
ERR_TRANSPORT_MERGE_CONFLICT = "TRANSPORT_MERGE_CONFLICT"
ERR_TRANSPORT_AUTH_FAILURE = "TRANSPORT_AUTH_FAILURE"
ERR_TRANSPORT_REPO_NOT_FOUND = "TRANSPORT_REPO_NOT_FOUND"
ERR_TRANSPORT_RATE_LIMITED = "TRANSPORT_RATE_LIMITED"
ERR_TRANSPORT_NETWORK_ERROR = "TRANSPORT_NETWORK_ERROR"

ERR_TRUST_SCORE_LOW = "TRUST_SCORE_LOW"
ERR_TRUST_POISONING = "TRUST_POISONING"
ERR_TRUST_UNKNOWN_AGENT = "TRUST_UNKNOWN_AGENT"
ERR_TRUST_ATTESTATION_FAILED = "TRUST_ATTESTATION_FAILED"

ERR_SPEC_OPCODE_CONFLICT = "SPEC_OPCODE_CONFLICT"
ERR_SPEC_FORMAT_VIOLATION = "SPEC_FORMAT_VIOLATION"
ERR_SPEC_ENCODING_ERROR = "SPEC_ENCODING_ERROR"
ERR_SPEC_MISSING_HANDLER = "SPEC_MISSING_HANDLER"
ERR_SPEC_VERSION_MISMATCH = "SPEC_VERSION_MISMATCH"
ERR_SPEC_UNKNOWN_OPCODE = "SPEC_UNKNOWN_OPCODE"

ERR_SECURITY_CAP_REQUIRED = "SECURITY_CAP_REQUIRED"
ERR_SECURITY_CAP_DENIED = "SECURITY_CAP_DENIED"
ERR_SECURITY_SANDBOX_VIOLATION = "SECURITY_SANDBOX_VIOLATION"
ERR_SECURITY_UNVERIFIED_BYTECODE = "SECURITY_UNVERIFIED_BYTECODE"

# Aggregate set for quick membership checks
ALL_ERROR_CODES = frozenset(ec.value for ec in ErrorCode)
