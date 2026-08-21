"""V2.0 Centralized configuration.

All runtime constants are configurable here. Environment variables
override defaults. No important constants should be hardcoded in
business logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val is not None:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is not None:
        return val.lower() in ("1", "true", "yes")
    return default


@dataclass
class Settings:
    """Centralized configuration for Zoey Spatial V2.0.

    All fields can be overridden via environment variables.
    """

    # ── Server ────────────────────────────────
    server_host: str = field(
        default_factory=lambda: _env_str("ZOEY_HOST", "0.0.0.0")
    )
    server_port: int = field(
        default_factory=lambda: _env_int("ZOEY_PORT", 8000)
    )
    cors_origins: str = field(
        default_factory=lambda: _env_str("ZOEY_CORS", "*")
    )

    # ── Vision ────────────────────────────────
    camera_index: int = field(
        default_factory=lambda: _env_int("ZOEY_CAMERA", 0)
    )
    model_path: str = field(
        default_factory=lambda: _env_str("ZOEY_MODEL", "models/hand_landmarker.task")
    )
    num_hands: int = field(
        default_factory=lambda: _env_int("ZOEY_NUM_HANDS", 2)
    )
    min_detection_confidence: float = field(
        default_factory=lambda: _env_float("ZOEY_DETECT_CONF", 0.5)
    )
    min_presence_confidence: float = field(
        default_factory=lambda: _env_float("ZOEY_PRESENCE_CONF", 0.5)
    )
    min_tracking_confidence: float = field(
        default_factory=lambda: _env_float("ZOEY_TRACKING_CONF", 0.5)
    )

    # ── Depth ─────────────────────────────────
    depth_scale: float = field(
        default_factory=lambda: _env_float("ZOEY_DEPTH_SCALE", 20.0)
    )
    depth_smoothing_alpha: float = field(
        default_factory=lambda: _env_float("ZOEY_DEPTH_ALPHA", 0.3)
    )

    # ── Gesture ───────────────────────────────
    gesture_smoother_window: int = field(
        default_factory=lambda: _env_int("ZOEY_GESTURE_WINDOW", 5)
    )
    pinch_distance_threshold: float = field(
        default_factory=lambda: _env_float("ZOEY_PINCH_DIST", 0.07)
    )

    # ── Interaction ───────────────────────────
    click_window: int = field(
        default_factory=lambda: _env_int("ZOEY_CLICK_WINDOW", 12)
    )
    double_click_window: int = field(
        default_factory=lambda: _env_int("ZOEY_DBLCLICK_WINDOW", 40)
    )
    click_grab_threshold: int = field(
        default_factory=lambda: _env_int("ZOEY_CLICK_GRAB_THRESH", 4)
    )
    click_position_tolerance: float = field(
        default_factory=lambda: _env_float("ZOEY_CLICK_POS_TOL", 0.05)
    )

    # ── Protocol ──────────────────────────────
    protocol_version: str = field(
        default_factory=lambda: _env_str("ZOEY_PROTOCOL_VERSION", "2.0")
    )
    ping_interval: float = field(
        default_factory=lambda: _env_float("ZOEY_PING_INTERVAL", 30.0)
    )

    # ── Logging ───────────────────────────────
    log_level: str = field(
        default_factory=lambda: _env_str("ZOEY_LOG_LEVEL", "INFO")
    )
    log_interaction: bool = field(
        default_factory=lambda: _env_bool("ZOEY_LOG_INTERACTION", False)
    )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing)."""
    global _settings
    _settings = None
