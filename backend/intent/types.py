"""V1.9 Intent types.

Typed intents that describe *what* the user wants to do,
independent of *how* it is executed. The IntentEngine produces
these; the ActionEngine consumes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IntentType(Enum):
    """All supported intent types."""

    GRAB = "GRAB"
    RELEASE = "RELEASE"
    SELECT = "SELECT"
    CLICK = "CLICK"
    MOVE = "MOVE"
    ROTATE = "ROTATE"
    SCALE = "SCALE"
    HOVER = "HOVER"
    CANCEL = "CANCEL"
    NAVIGATE = "NAVIGATE"


@dataclass(frozen=True)
class Intent:
    """A user intent resolved from one or more interaction events.

    Attributes:
        intent_type: What the user wants to do.
        target_object_id: Which object this applies to (may be None).
        hand_label: Which hand triggered this ("LEFT"/"RIGHT"/None).
        x, y, z: Position context at intent time.
        delta_x, delta_y, delta_z: Movement deltas for MOVE intents.
        rotation_delta: Rotation delta for ROTATE intents.
        scale_factor: Scale multiplier for SCALE intents.
        from_llm: Whether this intent was produced by the LLM.
    """

    intent_type: IntentType
    target_object_id: Optional[str] = None
    hand_label: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    delta_x: float = 0.0
    delta_y: float = 0.0
    delta_z: float = 0.0
    rotation_delta: float = 0.0
    scale_factor: float = 1.0
    from_llm: bool = False
