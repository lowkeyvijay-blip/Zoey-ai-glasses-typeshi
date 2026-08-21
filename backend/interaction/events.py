"""Interaction event types and data structures for V1.5-V1.7.

Typed events emitted by the EventDetector when interaction
state transitions occur. These are pure data — no behavior.

V1.6: Added hand_label for two-hand event attribution.
V1.7: Added hand_z for depth-aware event positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Types of interaction events."""

    GRAB = "GRAB"
    RELEASE = "RELEASE"
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    FREEZE = "FREEZE"
    RESUME = "RESUME"


@dataclass(frozen=True)
class InteractionEvent:
    """A single interaction event.

    Attributes:
        event_type: What happened.
        timestamp: Frame number when event occurred.
        hand_x: Normalized hand X at event time.
        hand_y: Normalized hand Y at event time.
        hand_z: World-space hand Z at event time (V1.7).
        hand_label: "LEFT" or "RIGHT" for two-hand tracking.
                    None for single-hand / unspecified.
    """

    event_type: EventType
    timestamp: int
    hand_x: float = 0.0
    hand_y: float = 0.0
    hand_z: float = 0.0
    hand_label: Optional[str] = None
