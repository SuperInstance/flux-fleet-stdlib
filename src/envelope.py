"""
flux-fleet-stdlib / envelope.py
Standardized message format for inter-agent (A2A) communication.

Every message exchanged between fleet agents is wrapped in a
``MessageEnvelope`` that carries metadata (type, priority, TTL, sender/
recipient addressing) alongside an arbitrary JSON-serializable payload.

All types support round-trip serialization.
"""

from __future__ import annotations

import enum
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .types import FleetAddress


# ---------------------------------------------------------------------------
# MessageType
# ---------------------------------------------------------------------------

class MessageType(str, enum.Enum):
    """Canonical A2A message types."""

    TELL = "TELL"
    ASK = "ASK"
    DELEGATE = "DELEGATE"
    BCAST = "BCAST"
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    REPORT = "REPORT"
    SIGNAL = "SIGNAL"
    STATUS = "STATUS"
    DISCOVER = "DISCOVER"
    HEARTBEAT = "HEARTBEAT"


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------

class Priority(str, enum.Enum):
    """Message priority levels (ascending severity)."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# MessageEnvelope
# ---------------------------------------------------------------------------

@dataclass
class MessageEnvelope:
    """Standardized envelope for inter-agent messages.

    Parameters
    ----------
    msg_id : str
        Unique identifier (UUID by default).
    msg_type : MessageType
        The kind of A2A message.
    sender : FleetAddress
        Who sent the message.
    recipient : FleetAddress
        Who should receive the message.
    priority : Priority
        Delivery priority.
    payload : dict
        Arbitrary structured data carried by the message.
    correlation_id : str
        Links request-response pairs.
    ttl_seconds : int
        Time-to-live in seconds (default 1 hour).
    created_at : float
        Unix timestamp of creation.
    reply_to : str
        ``msg_id`` of the original message being replied to.
    """

    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    msg_type: MessageType = MessageType.TELL
    sender: FleetAddress = field(default_factory=lambda: FleetAddress(name=""))
    recipient: FleetAddress = field(default_factory=lambda: FleetAddress(name=""))
    priority: Priority = Priority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    ttl_seconds: int = 3600
    created_at: float = field(default_factory=time.time)
    reply_to: str = ""

    # -- queries -------------------------------------------------------------

    def is_expired(self) -> bool:
        """Return ``True`` if the envelope has exceeded its TTL."""
        return (time.time() - self.created_at) > self.ttl_seconds

    # -- factory helpers -----------------------------------------------------

    def create_reply(
        self,
        payload: Dict[str, Any],
        msg_type: MessageType = MessageType.REPORT,
    ) -> "MessageEnvelope":
        """Create a reply envelope that references this message.

        The reply's ``sender`` becomes this envelope's ``recipient``, the
        reply's ``recipient`` becomes this envelope's ``sender``, and the
        ``correlation_id`` / ``reply_to`` fields are wired automatically.
        """
        return MessageEnvelope(
            msg_type=msg_type,
            sender=self.recipient,
            recipient=self.sender,
            priority=self.priority,
            payload=payload,
            correlation_id=self.correlation_id or self.msg_id,
            ttl_seconds=self.ttl_seconds,
            reply_to=self.msg_id,
        )

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "sender": self.sender.to_dict(),
            "recipient": self.recipient.to_dict(),
            "priority": self.priority.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at,
            "reply_to": self.reply_to,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MessageEnvelope":
        return cls(
            msg_id=d.get("msg_id", uuid.uuid4().hex),
            msg_type=MessageType(d.get("msg_type", "TELL")),
            sender=FleetAddress.from_dict(d.get("sender", {"name": ""})),
            recipient=FleetAddress.from_dict(d.get("recipient", {"name": ""})),
            priority=Priority(d.get("priority", "NORMAL")),
            payload=d.get("payload", {}),
            correlation_id=d.get("correlation_id", ""),
            ttl_seconds=d.get("ttl_seconds", 3600),
            created_at=d.get("created_at", time.time()),
            reply_to=d.get("reply_to", ""),
        )

    @classmethod
    def from_json(cls, s: str) -> "MessageEnvelope":
        return cls.from_dict(json.loads(s))
