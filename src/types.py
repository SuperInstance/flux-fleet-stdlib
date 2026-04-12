"""
flux-fleet-stdlib / types.py
Shared fleet data types.

These are the lingua-franca data structures that every fleet repo should use
when representing agents, tasks, repos, capabilities, and addressing.

All types support JSON serialization / deserialization for wire transport.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> float:
    return time.time()


def _stable_hash(*parts: str) -> str:
    """Deterministic SHA-256 truncated to 16 hex chars."""
    blob = "|".join(parts)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# AgentId
# ---------------------------------------------------------------------------

@dataclass
class AgentId:
    """Unique identity of a fleet agent."""

    name: str
    repo_url: str
    role: str = ""
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentId":
        return cls(**{k: d[k] for k in ("name", "repo_url", "role", "capabilities") if k in d})

    @classmethod
    def from_json(cls, s: str) -> "AgentId":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# TaskId
# ---------------------------------------------------------------------------

@dataclass
class TaskId:
    """Opaque, unique identifier for a cooperative task."""

    source_agent: str
    timestamp: float = field(default_factory=_ts)
    unique_hash: str = ""

    def __post_init__(self) -> None:
        if not self.unique_hash:
            self.unique_hash = _stable_hash(
                self.source_agent, str(self.timestamp)
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TaskId":
        return cls(**{k: d[k] for k in ("source_agent", "timestamp", "unique_hash") if k in d})

    @classmethod
    def from_json(cls, s: str) -> "TaskId":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# RepoRef
# ---------------------------------------------------------------------------

@dataclass
class RepoRef:
    """Pointer to a specific git repository state."""

    owner: str
    name: str
    branch: str = "main"
    commit_hash: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RepoRef":
        return cls(**{k: d[k] for k in ("owner", "name", "branch", "commit_hash") if k in d})

    @classmethod
    def from_json(cls, s: str) -> "RepoRef":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------

@dataclass
class Capability:
    """A named capability with a confidence score and optional evidence."""

    name: str
    confidence: float = 0.0
    evidence_url: str = ""

    def __post_init__(self) -> None:
        # Clamp to [0.0, 1.0]
        self.confidence = max(0.0, min(1.0, self.confidence))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Capability":
        return cls(**{k: d[k] for k in ("name", "confidence", "evidence_url") if k in d})

    @classmethod
    def from_json(cls, s: str) -> "Capability":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# FleetAddress
# ---------------------------------------------------------------------------

@dataclass
class FleetAddress:
    """Addressing pattern used to route messages within the fleet."""

    name: str
    role_pattern: str = "*"
    capability_pattern: str = "*"
    repo_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FleetAddress":
        return cls(**{
            k: d[k] for k in ("name", "role_pattern", "capability_pattern", "repo_url")
            if k in d
        })

    @classmethod
    def from_json(cls, s: str) -> "FleetAddress":
        return cls.from_dict(json.loads(s))
