"""Interaction event types and data structures for V1.5.

Typed events emitted by the EventDetector when interaction
state transitions occur. These are pure data — no behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
    """

    event_type: EventType
    timestamp: int
    hand_x: float = 0.0
    hand_y: float = 0.0
