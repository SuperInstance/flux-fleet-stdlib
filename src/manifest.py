"""
flux-fleet-stdlib / manifest.py
Agent capability manifest — the public "business card" every fleet agent publishes.

An ``AgentManifest`` declares what an agent can do (capabilities, supported
opcodes, formats) and what it needs (resources).  Other agents and the
orchestrator read manifests to decide delegation targets and compatibility.

All types support round-trip serialization via ``to_dict`` / ``from_dict`` /
``to_json`` / ``from_json``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# ResourceRequirements
# ---------------------------------------------------------------------------

@dataclass
class ResourceRequirements:
    """Declares the compute resources an agent needs to operate."""

    max_memory_mb: int = 256
    max_cpu_seconds: int = 60
    requires_gpu: bool = False
    requires_network: bool = False
    supported_formats: List[str] = field(
        default_factory=lambda: ["A", "B", "C", "D", "E"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_seconds": self.max_cpu_seconds,
            "requires_gpu": self.requires_gpu,
            "requires_network": self.requires_network,
            "supported_formats": list(self.supported_formats),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResourceRequirements":
        return cls(
            max_memory_mb=d.get("max_memory_mb", 256),
            max_cpu_seconds=d.get("max_cpu_seconds", 60),
            requires_gpu=d.get("requires_gpu", False),
            requires_network=d.get("requires_network", False),
            supported_formats=d.get("supported_formats", ["A", "B", "C", "D", "E"]),
        )

    @classmethod
    def from_json(cls, s: str) -> "ResourceRequirements":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# OpcodeSupport
# ---------------------------------------------------------------------------

@dataclass
class OpcodeSupport:
    """Declares support (or lack thereof) for a single opcode."""

    opcode: int
    mnemonic: str
    format: str  # A–G
    implemented: bool = False
    tested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opcode": self.opcode,
            "mnemonic": self.mnemonic,
            "format": self.format,
            "implemented": self.implemented,
            "tested": self.tested,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OpcodeSupport":
        return cls(
            opcode=d["opcode"],
            mnemonic=d["mnemonic"],
            format=d.get("format", "A"),
            implemented=d.get("implemented", False),
            tested=d.get("tested", False),
        )

    @classmethod
    def from_json(cls, s: str) -> "OpcodeSupport":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# AgentManifest
# ---------------------------------------------------------------------------

# Canonical agent roles
VALID_ROLES = ("lighthouse", "vessel", "scout", "workhorse")


@dataclass
class AgentManifest:
    """Comprehensive capability manifest published by every fleet agent.

    Fields
    ------
    agent_name : str
        Human-readable agent identifier (e.g. ``"executor-01"``).
    agent_role : str
        One of ``"lighthouse"``, ``"vessel"``, ``"scout"``, ``"workhorse"``.
    version : str
        Semantic version string (e.g. ``"0.3.1"``).
    capabilities : list[str]
        Named capabilities (e.g. ``["bytecode_execution", "a2a_tell"]``).
    opcode_support : list[OpcodeSupport]
        Per-opcode support declarations.
    resource_requirements : ResourceRequirements
        Compute resource needs.
    repo_url : str
        URL of the agent's source repository.
    test_count : int
        Number of tests the agent ships with (trust signal).
    last_active : float
        Unix timestamp of last heartbeat / activity.
    trust_baseline : float
        Initial trust score in ``[0.0, 1.0]``.
    """

    agent_name: str
    agent_role: str
    version: str
    capabilities: List[str] = field(default_factory=list)
    opcode_support: List[OpcodeSupport] = field(default_factory=list)
    resource_requirements: ResourceRequirements = field(
        default_factory=ResourceRequirements
    )
    repo_url: str = ""
    test_count: int = 0
    last_active: float = field(default_factory=time.time)
    trust_baseline: float = 0.5

    # -- queries -------------------------------------------------------------

    def supports_opcode(self, opcode: int) -> bool:
        """Return ``True`` if the agent has implemented the given opcode."""
        for op in self.opcode_support:
            if op.opcode == opcode:
                return op.implemented
        return False

    def supports_format(self, fmt: str) -> bool:
        """Return ``True`` if the agent handles the given bytecode format."""
        return fmt in self.resource_requirements.supported_formats

    def supports_capability(self, cap: str) -> bool:
        """Return ``True`` if the agent advertises the named capability."""
        return cap in self.capabilities

    def compatibility_score(self, other: AgentManifest) -> float:
        """Compute a ``[0.0, 1.0]`` compatibility score with *other*.

        Factors:
        * Overlap in supported formats (weight 0.25)
        * Overlap in capabilities (weight 0.35)
        * Overlap in implemented opcodes (weight 0.25)
        * Trust proximity (weight 0.15)
        """
        # Format overlap
        fmt_a = set(self.resource_requirements.supported_formats)
        fmt_b = set(other.resource_requirements.supported_formats)
        fmt_score = len(fmt_a & fmt_b) / max(len(fmt_a | fmt_b), 1)

        # Capability overlap
        cap_a = set(self.capabilities)
        cap_b = set(other.capabilities)
        cap_score = len(cap_a & cap_b) / max(len(cap_a | cap_b), 1)

        # Implemented opcode overlap
        impl_a = {op.opcode for op in self.opcode_support if op.implemented}
        impl_b = {op.opcode for op in other.opcode_support if op.implemented}
        opc_score = len(impl_a & impl_b) / max(len(impl_a | impl_b), 1)

        # Trust proximity (Jaccard-like on trust baseline)
        trust_diff = abs(self.trust_baseline - other.trust_baseline)
        trust_score = 1.0 - trust_diff  # 1.0 when equal, 0.0 at max distance

        return (
            0.25 * fmt_score
            + 0.35 * cap_score
            + 0.25 * opc_score
            + 0.15 * trust_score
        )

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "opcode_support": [op.to_dict() for op in self.opcode_support],
            "resource_requirements": self.resource_requirements.to_dict(),
            "repo_url": self.repo_url,
            "test_count": self.test_count,
            "last_active": self.last_active,
            "trust_baseline": self.trust_baseline,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentManifest":
        return cls(
            agent_name=d["agent_name"],
            agent_role=d["agent_role"],
            version=d["version"],
            capabilities=d.get("capabilities", []),
            opcode_support=[
                OpcodeSupport.from_dict(op) for op in d.get("opcode_support", [])
            ],
            resource_requirements=ResourceRequirements.from_dict(
                d.get("resource_requirements", {})
            ),
            repo_url=d.get("repo_url", ""),
            test_count=d.get("test_count", 0),
            last_active=d.get("last_active", time.time()),
            trust_baseline=d.get("trust_baseline", 0.5),
        )

    @classmethod
    def from_json(cls, s: str) -> "AgentManifest":
        return cls.from_dict(json.loads(s))
