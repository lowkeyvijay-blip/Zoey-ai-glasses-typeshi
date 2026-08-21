"""V2.0 Error handling package."""

from backend.errors.exceptions import (
    ZoeyError,
    CameraError,
    ModelError,
    ProtocolError,
    SceneError,
    ConfigError,
    PipelineError,
)

__all__ = [
    "ZoeyError",
    "CameraError",
    "ModelError",
    "ProtocolError",
    "SceneError",
    "ConfigError",
    "PipelineError",
]
