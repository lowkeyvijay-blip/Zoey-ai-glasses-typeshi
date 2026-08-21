"""Tests for V2.0 Configuration."""

import os
import pytest
from backend.config.settings import Settings, get_settings, reset_settings


class TestSettingsDefaults:
    def test_default_host(self):
        s = Settings()
        assert s.server_host == "0.0.0.0"

    def test_default_port(self):
        s = Settings()
        assert s.server_port == 8000

    def test_default_camera(self):
        s = Settings()
        assert s.camera_index == 0

    def test_default_depth_scale(self):
        s = Settings()
        assert s.depth_scale == 20.0

    def test_default_model_path(self):
        s = Settings()
        assert "hand_landmarker.task" in s.model_path

    def test_default_num_hands(self):
        s = Settings()
        assert s.num_hands == 2

    def test_default_log_level(self):
        s = Settings()
        assert s.log_level == "INFO"

    def test_default_protocol_version(self):
        s = Settings()
        assert s.protocol_version == "2.0"

    def test_default_click_window(self):
        s = Settings()
        assert s.click_window == 12

    def test_default_gesture_window(self):
        s = Settings()
        assert s.gesture_smoother_window == 5


class TestEnvOverrides:
    def test_env_host(self, monkeypatch):
        monkeypatch.setenv("ZOEY_HOST", "127.0.0.1")
        s = Settings()
        assert s.server_host == "127.0.0.1"

    def test_env_port(self, monkeypatch):
        monkeypatch.setenv("ZOEY_PORT", "9000")
        s = Settings()
        assert s.server_port == 9000

    def test_env_depth_scale(self, monkeypatch):
        monkeypatch.setenv("ZOEY_DEPTH_SCALE", "10.5")
        s = Settings()
        assert s.depth_scale == 10.5

    def test_env_bool_true(self, monkeypatch):
        monkeypatch.setenv("ZOEY_LOG_INTERACTION", "true")
        s = Settings()
        assert s.log_interaction is True

    def test_env_bool_false(self, monkeypatch):
        monkeypatch.setenv("ZOEY_LOG_INTERACTION", "false")
        s = Settings()
        assert s.log_interaction is False

    def test_env_invalid_int_keeps_default(self, monkeypatch):
        monkeypatch.setenv("ZOEY_PORT", "notanumber")
        s = Settings()
        assert s.server_port == 8000

    def test_env_invalid_float_keeps_default(self, monkeypatch):
        monkeypatch.setenv("ZOEY_DEPTH_SCALE", "xyz")
        s = Settings()
        assert s.depth_scale == 20.0


class TestSettingsSingleton:
    def test_get_settings_returns_same(self):
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_settings(self):
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2
