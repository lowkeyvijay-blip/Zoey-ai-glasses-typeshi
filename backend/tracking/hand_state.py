"""V2.0 Hand tracking state.

Clean hand tracking state independent from raw MediaPipe output.
Supports left/right hands independently with position history,
confidence, and detection status.

Does NOT duplicate existing gesture or interaction state machines.
This is supplementary tracking metadata.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Optional


class HandId(Enum):
    """Hand identity."""
    LEFT = "LEFT"
    RIGHT = "RIGHT"


@dataclass
class HandTrackingState:
    """Clean hand tracking state for one hand.

    Attributes:
        hand_id: Left or right hand identity.
        detected: Whether the hand is currently detected.
        x, y, z: Current position.
        gesture: Current gesture label.
        confidence: Detection confidence if available.
        position_history: Recent position samples.
        last_update_frame: Frame number of last update.
        tracking_id: MediaPipe tracking ID if available.
    """

    hand_id: HandId
    detected: bool = False
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    gesture: str = "NO_HAND"
    confidence: float = 0.0
    position_history: Deque = field(default_factory=lambda: deque(maxlen=30))
    last_update_frame: int = 0
    tracking_id: Optional[int] = None

    def update(
        self,
        x: float,
        y: float,
        z: float,
        gesture: str,
        frame: int,
        confidence: float = 0.0,
        tracking_id: Optional[int] = None,
    ) -> None:
        """Update tracking state with new data."""
        self.x = x
        self.y = y
        self.z = z
        self.gesture = gesture
        self.confidence = confidence
        self.detected = True
        self.last_update_frame = frame
        self.tracking_id = tracking_id
        self.position_history.append((x, y, z))

    def clear(self) -> None:
        """Mark hand as not detected."""
        self.detected = False
        self.gesture = "NO_HAND"
        self.confidence = 0.0
        self.tracking_id = None

    @property
    def position(self) -> tuple:
        """Current position as (x, y, z)."""
        return (self.x, self.y, self.z)

    @property
    def velocity(self) -> tuple:
        """Approximate velocity from position history."""
        if len(self.position_history) < 2:
            return (0.0, 0.0, 0.0)
        prev = self.position_history[-2]
        curr = self.position_history[-1]
        return (
            curr[0] - prev[0],
            curr[1] - prev[1],
            curr[2] - prev[2],
        )

    @property
    def frames_since_update(self) -> int:
        """How many frames since last detection update."""
        return -1  # Requires frame counter externally

    def to_dict(self) -> dict:
        """Serialize for debugging/protocol."""
        return {
            "hand_id": self.hand_id.value,
            "detected": self.detected,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "gesture": self.gesture,
            "confidence": self.confidence,
            "history_length": len(self.position_history),
        }
