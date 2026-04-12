"""
flux-fleet-stdlib / versioning.py
ISA version comparison and opcode mapping between ISA revisions.

Provides ``ISAVersion`` for semantic versioning of the fleet's instruction-set
architecture and ``OpcodeMapping`` for translating opcodes between ISA versions.

All types support round-trip serialization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict


# ---------------------------------------------------------------------------
# ISAVersion
# ---------------------------------------------------------------------------

@dataclass
class ISAVersion:
    """Semantic version for the fleet instruction-set architecture.

    Parameters
    ----------
    major : int
        Breaking-change counter.
    minor : int
        Feature-addition counter (backwards-compatible).
    patch : int
        Bug-fix counter.
    label : str
        Optional human-readable label (e.g. ``"v2"``, ``"unified"``,
        ``"converged"``).
    """

    major: int
    minor: int
    patch: int
    label: str = ""

    def __str__(self) -> str:
        """Render as ``"{major}.{minor}.{patch}[-{label}]"``."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.label:
            return f"{base}-{self.label}"
        return base

    def __repr__(self) -> str:
        return f"ISAVersion({self!s})"

    def compatible_with(self, other: ISAVersion) -> bool:
        """Two ISA versions are compatible when their *major* numbers match.

        Minor and patch differences are acceptable; a label mismatch alone
        does **not** break compatibility.
        """
        return self.major == other.major

    # -- comparison helpers --------------------------------------------------

    def _tuple(self) -> tuple:
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ISAVersion):
            return NotImplemented
        return self._tuple() < other._tuple()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, ISAVersion):
            return NotImplemented
        return self._tuple() <= other._tuple()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, ISAVersion):
            return NotImplemented
        return self._tuple() > other._tuple()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, ISAVersion):
            return NotImplemented
        return self._tuple() >= other._tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ISAVersion):
            return NotImplemented
        return self._tuple() == other._tuple() and self.label == other.label

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.label))

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "label": self.label,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ISAVersion":
        return cls(
            major=d.get("major", 0),
            minor=d.get("minor", 0),
            patch=d.get("patch", 0),
            label=d.get("label", ""),
        )

    @classmethod
    def from_json(cls, s: str) -> "ISAVersion":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# OpcodeMapping
# ---------------------------------------------------------------------------

@dataclass
class OpcodeMapping:
    """Maps a single opcode from one ISA revision to another.

    Parameters
    ----------
    mnemonic : str
        Human-readable opcode name (e.g. ``"ADD"``).
    source_code : int
        Numeric opcode in the *source* ISA.
    target_code : int
        Numeric opcode in the *target* ISA.
    format : str
        Bytecode format tag (A–G).
    """

    mnemonic: str
    source_code: int
    target_code: int
    format: str = "A"

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mnemonic": self.mnemonic,
            "source_code": self.source_code,
            "target_code": self.target_code,
            "format": self.format,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OpcodeMapping":
        return cls(
            mnemonic=d["mnemonic"],
            source_code=d["source_code"],
            target_code=d["target_code"],
            format=d.get("format", "A"),
        )

    @classmethod
    def from_json(cls, s: str) -> "OpcodeMapping":
        return cls.from_dict(json.loads(s))
