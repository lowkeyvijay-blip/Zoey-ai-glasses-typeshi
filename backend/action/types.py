"""V1.9 Action types.

Typed actions that describe *what change* to make to the Scene.
The ActionEngine produces these from Intents and applies them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ActionType(Enum):
    """All supported action types."""

    MOVE_OBJECT = "MOVE_OBJECT"
    ROTATE_OBJECT = "ROTATE_OBJECT"
    SCALE_OBJECT = "SCALE_OBJECT"
    SELECT_OBJECT = "SELECT_OBJECT"
    OPEN_PANEL = "OPEN_PANEL"
    CLOSE_PANEL = "CLOSE_PANEL"
    NAVIGATE = "NAVIGATE"


@dataclass(frozen=True)
class Action:
    """A concrete action to apply to the Scene.

    Attributes:
        action_type: What change to make.
        target_object_id: Which object to modify.
        x, y, z: Absolute or delta position.
        dx, dy, dz: Position deltas.
        rotation_delta: Rotation change in radians.
        scale_factor: Scale multiplier.
    """

    action_type: ActionType
    target_object_id: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    rotation_delta: float = 0.0
    scale_factor: float = 1.0
