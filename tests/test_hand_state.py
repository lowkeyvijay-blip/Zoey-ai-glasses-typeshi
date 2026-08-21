"""Tests for V2.0 Hand Tracking State."""

import pytest
from backend.tracking.hand_state import HandTrackingState, HandId


class TestHandTrackingState:
    def test_create_left(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        assert hs.hand_id == HandId.LEFT
        assert hs.detected is False
        assert hs.gesture == "NO_HAND"

    def test_create_right(self):
        hs = HandTrackingState(hand_id=HandId.RIGHT)
        assert hs.hand_id == HandId.RIGHT

    def test_update(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(x=0.5, y=0.3, z=1.0, gesture="PINCH", frame=10)
        assert hs.detected is True
        assert hs.x == 0.5
        assert hs.y == 0.3
        assert hs.z == 1.0
        assert hs.gesture == "PINCH"
        assert hs.last_update_frame == 10

    def test_position_history(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(0.1, 0.2, 0.3, "OPEN_PALM", 1)
        hs.update(0.4, 0.5, 0.6, "PINCH", 2)
        assert len(hs.position_history) == 2
        assert hs.position_history[0] == (0.1, 0.2, 0.3)
        assert hs.position_history[1] == (0.4, 0.5, 0.6)

    def test_position_history_maxlen(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        for i in range(40):
            hs.update(float(i), 0.0, 0.0, "PINCH", i)
        assert len(hs.position_history) == 30

    def test_clear(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(0.5, 0.3, 1.0, "PINCH", 10)
        assert hs.detected is True
        hs.clear()
        assert hs.detected is False
        assert hs.gesture == "NO_HAND"

    def test_velocity_zero_when_empty(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        assert hs.velocity == (0.0, 0.0, 0.0)

    def test_velocity_zero_when_one_sample(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(0.5, 0.3, 1.0, "PINCH", 1)
        assert hs.velocity == (0.0, 0.0, 0.0)

    def test_velocity_computed(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(0.5, 0.3, 1.0, "PINCH", 1)
        hs.update(0.6, 0.4, 1.1, "PINCH", 2)
        vx, vy, vz = hs.velocity
        assert vx == pytest.approx(0.1)
        assert vy == pytest.approx(0.1)
        assert vz == pytest.approx(0.1)

    def test_to_dict(self):
        hs = HandTrackingState(hand_id=HandId.LEFT)
        hs.update(0.5, 0.3, 1.0, "PINCH", 10, confidence=0.95)
        d = hs.to_dict()
        assert d["hand_id"] == "LEFT"
        assert d["detected"] is True
        assert d["gesture"] == "PINCH"
        assert d["confidence"] == 0.95

    def test_position_property(self):
        hs = HandTrackingState(hand_id=HandId.RIGHT)
        hs.update(0.5, 0.3, 1.0, "PINCH", 1)
        assert hs.position == (0.5, 0.3, 1.0)
