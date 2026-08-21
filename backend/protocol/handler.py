"""V2.0 Protocol handler.

Manages WebSocket protocol: handshake, version negotiation,
session management, ping/pong, graceful malformed-message handling.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from backend.protocol.messages import (
    PROTOCOL_VERSION,
    SERVER_ID,
    HandshakeAckMessage,
    HandshakeMessage,
    ErrorMessage,
    MessageType,
    PingMessage,
    PongMessage,
    ProtocolMessage,
)

logger = logging.getLogger(__name__)


class ProtocolHandler:
    """Manages per-connection protocol state.

    Handles handshake, version negotiation, message parsing,
    and ping/pong keepalive.
    """

    def __init__(self, session_id: str = "") -> None:
        self._session_id = session_id
        self._handshake_complete = False
        self._client_version: Optional[str] = None
        self._compatible = True

    @property
    def handshake_complete(self) -> bool:
        return self._handshake_complete

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def compatible(self) -> bool:
        return self._compatible

    def parse_message(self, raw: str) -> Optional[ProtocolMessage]:
        """Parse a raw JSON string into a ProtocolMessage.

        Returns None for malformed messages (does not crash).
        """
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "[%s] Malformed JSON received", self._session_id
            )
            return None

        if not isinstance(data, dict):
            logger.warning(
                "[%s] Non-dict message received", self._session_id
            )
            return None

        msg_type_str = data.get("type", "unknown")

        try:
            msg_type = MessageType(msg_type_str)
        except ValueError:
            logger.warning(
                "[%s] Unknown message type: %s",
                self._session_id,
                msg_type_str,
            )
            return ProtocolMessage(type=MessageType.UNKNOWN)

        version = data.get("version", PROTOCOL_VERSION)

        if msg_type == MessageType.HANDSHAKE:
            return HandshakeMessage(
                version=version,
                capabilities=data.get("capabilities", []),
            )

        if msg_type == MessageType.PING:
            return PingMessage(version=version)

        if msg_type == MessageType.PONG:
            return PongMessage(version=version)

        return ProtocolMessage(type=msg_type, version=version)

    def handle_handshake(
        self, msg: HandshakeMessage
    ) -> HandshakeAckMessage:
        """Process a handshake message and produce an ack."""
        self._client_version = msg.version
        self._compatible = self._is_compatible(msg.version)
        self._handshake_complete = True

        logger.info(
            "[%s] Handshake: client=%s compatible=%s",
            self._session_id,
            msg.version,
            self._compatible,
        )

        return HandshakeAckMessage(
            version=PROTOCOL_VERSION,
            server_id=SERVER_ID,
            compatible=self._compatible,
        )

    def handle_ping(self) -> PongMessage:
        """Respond to a ping with a pong."""
        return PongMessage(version=PROTOCOL_VERSION)

    def create_error(self, error: str, code: int = 400) -> ErrorMessage:
        """Create an error message."""
        return ErrorMessage(
            version=PROTOCOL_VERSION,
            error=error,
            code=code,
        )

    def _is_compatible(self, client_version: str) -> bool:
        """Check version compatibility (major version match)."""
        try:
            client_major = float(client_version)
            server_major = float(PROTOCOL_VERSION)
            return int(client_major) == int(server_major)
        except (ValueError, TypeError):
            return False
