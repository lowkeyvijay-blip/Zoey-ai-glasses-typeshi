"""V2.0 Protocol messages.

Typed/versioned messages for WebSocket communication.
All messages have a type field and version compatibility.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(Enum):
    """All supported message types."""
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    STATE_UPDATE = "state_update"
    EVENT = "event"
    INTENT = "intent"
    ACTION = "action"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    UNKNOWN = "unknown"


PROTOCOL_VERSION = "2.0"
SERVER_ID = "zoey-local"


@dataclass
class ProtocolMessage:
    """Base protocol message."""
    type: MessageType
    version: str = PROTOCOL_VERSION
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "version": self.version,
            "timestamp": self.timestamp,
        }


@dataclass
class HandshakeMessage(ProtocolMessage):
    """Client handshake request."""
    capabilities: List[str] = field(default_factory=list)

    def __init__(
        self,
        version: str = PROTOCOL_VERSION,
        capabilities: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(type=MessageType.HANDSHAKE, version=version, **kwargs)
        self.capabilities = capabilities or []

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["capabilities"] = self.capabilities
        return d


@dataclass
class HandshakeAckMessage(ProtocolMessage):
    """Server handshake acknowledgment."""
    server_id: str = SERVER_ID
    compatible: bool = True

    def __init__(
        self,
        version: str = PROTOCOL_VERSION,
        server_id: str = SERVER_ID,
        compatible: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(type=MessageType.HANDSHAKE_ACK, version=version, **kwargs)
        self.server_id = server_id
        self.compatible = compatible

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["server_id"] = self.server_id
        d["compatible"] = self.compatible
        return d


@dataclass
class StateUpdateMessage(ProtocolMessage):
    """Server state update (scene + interaction)."""
    state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["state"] = self.state
        return d


@dataclass
class EventMessage(ProtocolMessage):
    """Interaction event."""
    event_type: str = ""
    hand_label: str = ""
    object_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["event_type"] = self.event_type
        d["hand_label"] = self.hand_label
        d["object_id"] = self.object_id
        d["data"] = self.data
        return d


@dataclass
class IntentMessage(ProtocolMessage):
    """Resolved intent."""
    intent_type: str = ""
    target_object_id: str = ""
    from_llm: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["intent_type"] = self.intent_type
        d["target_object_id"] = self.target_object_id
        d["from_llm"] = self.from_llm
        return d


@dataclass
class PingMessage(ProtocolMessage):
    """Keepalive ping."""
    def __init__(self, **kwargs) -> None:
        super().__init__(type=MessageType.PING, **kwargs)


@dataclass
class PongMessage(ProtocolMessage):
    """Keepalive pong."""
    def __init__(self, **kwargs) -> None:
        super().__init__(type=MessageType.PONG, **kwargs)


@dataclass
class ErrorMessage(ProtocolMessage):
    """Error message."""
    error: str = ""
    code: int = 0

    def __init__(
        self,
        error: str = "",
        code: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(type=MessageType.ERROR, **kwargs)
        self.error = error
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["error"] = self.error
        d["code"] = self.code
        return d
