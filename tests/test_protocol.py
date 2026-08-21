"""Tests for V2.0 Protocol handler and messages."""

import json
import pytest
from backend.protocol.messages import (
    MessageType,
    ProtocolMessage,
    HandshakeMessage,
    HandshakeAckMessage,
    PingMessage,
    PongMessage,
    ErrorMessage,
    PROTOCOL_VERSION,
    SERVER_ID,
)
from backend.protocol.handler import ProtocolHandler


class TestProtocolMessages:
    def test_message_type_enum(self):
        assert MessageType.HANDSHAKE.value == "handshake"
        assert MessageType.PING.value == "ping"

    def test_protocol_message_to_dict(self):
        msg = ProtocolMessage(type=MessageType.EVENT)
        d = msg.to_dict()
        assert d["type"] == "event"
        assert "version" in d
        assert "timestamp" in d

    def test_handshake_message(self):
        msg = HandshakeMessage(version="2.0", capabilities=["state"])
        d = msg.to_dict()
        assert d["type"] == "handshake"
        assert d["version"] == "2.0"
        assert d["capabilities"] == ["state"]

    def test_handshake_ack(self):
        msg = HandshakeAckMessage(version="2.0", server_id="zoey-local")
        d = msg.to_dict()
        assert d["type"] == "handshake_ack"
        assert d["server_id"] == "zoey-local"
        assert d["compatible"] is True

    def test_ping_message(self):
        msg = PingMessage()
        assert msg.type == MessageType.PING

    def test_pong_message(self):
        msg = PongMessage()
        assert msg.type == MessageType.PONG

    def test_error_message(self):
        msg = ErrorMessage(error="bad request", code=400)
        d = msg.to_dict()
        assert d["error"] == "bad request"
        assert d["code"] == 400

    def test_protocol_version(self):
        assert PROTOCOL_VERSION == "2.0"

    def test_server_id(self):
        assert SERVER_ID == "zoey-local"


class TestProtocolHandler:
    def test_parse_valid_handshake(self):
        handler = ProtocolHandler(session_id="test")
        raw = json.dumps({"type": "handshake", "version": "2.0", "capabilities": []})
        msg = handler.parse_message(raw)
        assert isinstance(msg, HandshakeMessage)
        assert msg.version == "2.0"

    def test_parse_valid_ping(self):
        handler = ProtocolHandler(session_id="test")
        raw = json.dumps({"type": "ping"})
        msg = handler.parse_message(raw)
        assert isinstance(msg, PingMessage)

    def test_parse_malformed_json(self):
        handler = ProtocolHandler(session_id="test")
        msg = handler.parse_message("not json {{{")
        assert msg is None

    def test_parse_non_dict(self):
        handler = ProtocolHandler(session_id="test")
        msg = handler.parse_message('"just a string"')
        assert msg is None

    def test_parse_unknown_type(self):
        handler = ProtocolHandler(session_id="test")
        raw = json.dumps({"type": "nonexistent"})
        msg = handler.parse_message(raw)
        assert msg is not None
        assert msg.type == MessageType.UNKNOWN

    def test_handle_handshake(self):
        handler = ProtocolHandler(session_id="test")
        req = HandshakeMessage(version="2.0")
        ack = handler.handle_handshake(req)
        assert isinstance(ack, HandshakeAckMessage)
        assert ack.compatible is True
        assert handler.handshake_complete is True

    def test_handle_handshake_incompatible(self):
        handler = ProtocolHandler(session_id="test")
        req = HandshakeMessage(version="1.0")
        ack = handler.handle_handshake(req)
        assert ack.compatible is False

    def test_handle_ping(self):
        handler = ProtocolHandler(session_id="test")
        pong = handler.handle_ping()
        assert isinstance(pong, PongMessage)

    def test_create_error(self):
        handler = ProtocolHandler(session_id="test")
        err = handler.create_error("bad input", 422)
        assert err.error == "bad input"
        assert err.code == 422

    def test_session_id(self):
        handler = ProtocolHandler(session_id="abc123")
        assert handler.session_id == "abc123"

    def test_handshake_not_complete_initially(self):
        handler = ProtocolHandler(session_id="test")
        assert handler.handshake_complete is False

    def test_compatible_default(self):
        handler = ProtocolHandler(session_id="test")
        assert handler.compatible is True

    def test_parse_empty_string(self):
        handler = ProtocolHandler(session_id="test")
        msg = handler.parse_message("")
        assert msg is None

    def test_parse_non_string(self):
        handler = ProtocolHandler(session_id="test")
        msg = handler.parse_message(None)
        assert msg is None
