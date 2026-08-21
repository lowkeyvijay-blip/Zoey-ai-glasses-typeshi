"""V2.0 Exception hierarchy.

Clean exception types for all Zoey Spatial subsystems.
All exceptions inherit from ZoeyError for easy catching.
"""


class ZoeyError(Exception):
    """Base exception for all Zoey Spatial errors."""


class CameraError(ZoeyError):
    """Camera initialization, read, or release failure."""


class ModelError(ZoeyError):
    """MediaPipe model loading or inference failure."""


class ProtocolError(ZoeyError):
    """WebSocket protocol errors (malformed messages, version mismatch)."""


class SceneError(ZoeyError):
    """Scene registry or object manipulation errors."""


class ConfigError(ZoeyError):
    """Configuration validation errors."""


class PipelineError(ZoeyError):
    """Pipeline processing errors."""
