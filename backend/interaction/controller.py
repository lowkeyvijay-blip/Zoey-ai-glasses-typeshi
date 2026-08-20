"""Spatial interaction controller.

Manages the IDLE/GRABBED state machine for single-hand
spatial grab interactions.

Rules:
  - PINCH while IDLE → GRABBED, capture hand-to-sphere offset
  - PINCH while GRABBED → continue following (sphere = hand + offset)
  - OPEN_PALM while GRABBED → IDLE (release)
  - POINT/FIST/RELAXED/UNKNOWN while GRABBED → freeze sphere, stay GRABBED
  - NO_HAND → immediately release, sphere stays at last position

V1.4: No hover, no collision, no object selection.
      PINCH anywhere immediately grabs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InteractionState(Enum):
    IDLE = "IDLE"
    GRABBED = "GRABBED"


@dataclass
class HandPosition:
    """Normalized camera-space hand position."""
    x: float
    y: float


@dataclass
class SphereState:
    """Authoritative sphere position in world space."""
    x: float = 0.0
    y: float = 0.0


@dataclass
class GrabOffset:
    """Offset between hand and sphere center at grab moment.
    Prevents the sphere from jumping when first grabbed."""
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class InteractionResult:
    """Result of a single frame of interaction processing."""
    state: InteractionState
    sphere_position: SphereState
    hand_position: Optional[HandPosition]
    interaction_state: str


class SpatialInteractionController:
    """IDLE/GRABBED interaction state machine.

    Each WebSocket session should have its own controller instance.
    The controller is purely deterministic — no I/O, no global state.
    """

    def __init__(self) -> None:
        self._state: InteractionState = InteractionState.IDLE
        self._sphere: SphereState = SphereState()
        self._offset: GrabOffset = GrabOffset()
        self._hand: Optional[HandPosition] = None

    @property
    def state(self) -> InteractionState:
        return self._state

    @property
    def sphere_position(self) -> SphereState:
        return self._sphere

    def process_frame(
        self,
        gesture: str,
        hand_x: Optional[float] = None,
        hand_y: Optional[float] = None,
    ) -> InteractionResult:
        """Process one frame of gesture + hand position data.

        Args:
            gesture: The smoothed gesture label.
                     One of: PINCH, OPEN_PALM, POINT, FIST,
                     RELAXED, UNKNOWN, NO_HAND
            hand_x: Normalized hand X position (0-1). None if no hand.
            hand_y: Normalized hand Y position (0-1). None if no hand.

        Returns:
            InteractionResult with current state and sphere position.
        """

        has_hand = (
            hand_x is not None
            and hand_y is not None
        )

        if has_hand:
            self._hand = HandPosition(
                x=hand_x,
                y=hand_y,
            )
        else:
            self._hand = None

        # ── NO_HAND: immediately release ──

        if gesture == "NO_HAND":
            if self._state == InteractionState.GRABBED:
                self._release()
            return self._result()

        # ── PINCH while IDLE: grab ──

        if (
            gesture == "PINCH"
            and self._state == InteractionState.IDLE
            and has_hand
        ):
            self._grab(hand_x, hand_y)
            return self._result()

        # ── PINCH while GRABBED: follow ──

        if (
            gesture == "PINCH"
            and self._state == InteractionState.GRABBED
            and has_hand
        ):
            self._sphere.x = hand_x + self._offset.dx
            self._sphere.y = hand_y + self._offset.dy
            return self._result()

        # ── OPEN_PALM while GRABBED: release ──

        if (
            gesture == "OPEN_PALM"
            and self._state == InteractionState.GRABBED
        ):
            self._release()
            return self._result()

        # ── Everything else: freeze ──
        # POINT/FIST/RELAXED/UNKNOWN while GRABBED → stay GRABBED, don't move
        # Any gesture while IDLE → stay IDLE

        return self._result()

    def _grab(self, hand_x: float, hand_y: float) -> None:
        """Enter GRABBED state. Capture offset to prevent jump."""
        self._offset.dx = self._sphere.x - hand_x
        self._offset.dy = self._sphere.y - hand_y
        self._state = InteractionState.GRABBED

    def _release(self) -> None:
        """Return to IDLE. Sphere keeps its last position."""
        self._state = InteractionState.IDLE

    def _result(self) -> InteractionResult:
        """Build the current frame result."""
        return InteractionResult(
            state=self._state,
            sphere_position=SphereState(
                x=self._sphere.x,
                y=self._sphere.y,
            ),
            hand_position=(
                HandPosition(
                    x=self._hand.x,
                    y=self._hand.y,
                )
                if self._hand
                else None
            ),
            interaction_state=self._state.value,
        )
