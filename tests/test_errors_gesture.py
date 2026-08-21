"""Tests for V2.0 error handling and gesture hardening."""

import pytest
from backend.errors.exceptions import (
    ZoeyError,
    CameraError,
    ModelError,
    ProtocolError,
    SceneError,
    ConfigError,
    PipelineError,
)
from backend.gestures.gesture_engine import detect_gesture


class TestExceptionHierarchy:
    def test_base_exception(self):
        with pytest.raises(ZoeyError):
            raise ZoeyError("test")

    def test_camera_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise CameraError("camera failed")

    def test_model_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise ModelError("model failed")

    def test_protocol_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise ProtocolError("bad message")

    def test_scene_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise SceneError("object not found")

    def test_config_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise ConfigError("bad config")

    def test_pipeline_error_is_zoey(self):
        with pytest.raises(ZoeyError):
            raise PipelineError("pipeline failed")


class TestGestureHardening:
    def test_none_hand(self):
        assert detect_gesture(None) == "UNKNOWN"

    def test_empty_hand(self):
        assert detect_gesture([]) == "UNKNOWN"

    def test_short_hand(self):
        assert detect_gesture([None] * 10) == "UNKNOWN"

    def test_invalid_landmarks(self):
        class FakeLandmark:
            x = 0.5
            y = 0.5
            z = 0.0
        hand = [FakeLandmark() for _ in range(21)]
        result = detect_gesture(hand)
        assert result in ("PINCH", "POINT", "OPEN_PALM", "FIST", "RELAXED", "UNKNOWN")
