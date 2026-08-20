"""Spatial interaction controller.

Manages the IDLE/GRABBED state machine for single-hand
and two-hand spatial grab interactions.

Rules (V1.4 single-hand):
  - PINCH while IDLE → GRABBED, capture hand-to-sphere offset
  - PINCH while GRABBED → continue following (sphere = hand + offset)
  - OPEN_PALM while GRABBED → IDLE (release)
  - POINT/FIST/RELAXED/UNKNOWN while GRABBED → freeze sphere, stay GRABBED
  - NO_HAND → immediately release, sphere stays at last position

V1.4: No hover, no collision, no object selection.
      PINCH anywhere immediately grabs.

V1.6: Two-hand interaction.
  - Each hand tracked independently (LEFT/RIGHT)
  - When both hands grab, sphere controlled cooperatively
  - Distance between hands drives scale
  - Angle between hands drives rotation
  - One hand disappearing never corrupts the other hand's state
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InteractionState(Enum):
    IDLE = "IDLE"
    GRABBED = "GRABBED"


class HandLabel(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


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


# ─────────────────────────────────────────────────
# V1.6: Two-Hand Interaction
# ─────────────────────────────────────────────────


@dataclass
class SphereStateExtended:
    """Extended sphere state with scale and rotation."""
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0


@dataclass
class PerHandState:
    """Independent per-hand tracking state."""
    label: HandLabel = HandLabel.LEFT
    state: InteractionState = InteractionState.IDLE
    offset: GrabOffset = field(default_factory=GrabOffset)
    hand: Optional[HandPosition] = None
    frozen: bool = False


@dataclass
class TwoHandResult:
    """Result of a single frame of two-hand interaction processing."""
    sphere_position: SphereStateExtended
    interaction_state: str
    left_state: InteractionState
    right_state: InteractionState
    left_hand: Optional[HandPosition]
    right_hand: Optional[HandPosition]


class TwoHandController:
    """Two-hand spatial interaction controller.

    Manages independent per-hand IDLE/GRABBED states and a shared
    sphere with cooperative two-hand control (scale, rotation).

    When one hand grabs: single-hand mode (identical to V1.4).
    When both hands grab: cooperative mode with midpoint control,
    distance-based scaling, and angle-based rotation.

    Rules:
      - PINCH anywhere immediately grabs (V1.4 preserved).
      - Each hand's grab/release/freeze is independent.
      - Two hands never reset each other's interaction state.
      - One hand disappearing never corrupts the remaining hand.
    """

    def __init__(self) -> None:
        self._hands: dict[HandLabel, PerHandState] = {
            HandLabel.LEFT: PerHandState(label=HandLabel.LEFT),
            HandLabel.RIGHT: PerHandState(label=HandLabel.RIGHT),
        }
        self._sphere = SphereStateExtended()
        self._two_hand_offset = GrabOffset()
        self._initial_distance: Optional[float] = None
        self._initial_angle: Optional[float] = None
        self._was_two_hand: bool = False

    @property
    def sphere_position(self) -> SphereStateExtended:
        return self._sphere

    def process_frame(
        self,
        left_gesture: str = "NO_HAND",
        left_x: Optional[float] = None,
        left_y: Optional[float] = None,
        right_gesture: str = "NO_HAND",
        right_x: Optional[float] = None,
        right_y: Optional[float] = None,
    ) -> TwoHandResult:
        """Process one frame of multi-hand gesture data.

        Each hand is processed independently. Then the combined
        sphere state is computed based on how many hands are grabbing.
        """
        # ── Process each hand independently ──

        self._process_hand(
            HandLabel.LEFT, left_gesture, left_x, left_y
        )
        self._process_hand(
            HandLabel.RIGHT, right_gesture, right_x, right_y
        )

        # ── Compute combined sphere state ──

        left = self._hands[HandLabel.LEFT]
        right = self._hands[HandLabel.RIGHT]

        left_grabbed = left.state == InteractionState.GRABBED
        right_grabbed = right.state == InteractionState.GRABBED

        if left_grabbed and right_grabbed:
            self._update_two_hand()
        elif left_grabbed:
            self._update_single_hand(left)
        elif right_grabbed:
            self._update_single_hand(right)
        else:
            # Neither hand grabbing — sphere stays, reset two-hand state
            self._reset_two_hand_tracking()

        return self._result()

    def _process_hand(
        self,
        label: HandLabel,
        gesture: str,
        hand_x: Optional[float],
        hand_y: Optional[float],
    ) -> None:
        """Process one hand independently (V1.4 logic)."""
        hand = self._hands[label]
        has_hand = hand_x is not None and hand_y is not None

        if has_hand:
            hand.hand = HandPosition(x=hand_x, y=hand_y)
        else:
            hand.hand = None

        # ── NO_HAND: immediately release ──

        if gesture == "NO_HAND":
            if hand.state == InteractionState.GRABBED:
                hand.state = InteractionState.IDLE
                hand.frozen = False
            return

        # ── PINCH while IDLE: grab (immediate, no hover) ──

        if (
            gesture == "PINCH"
            and hand.state == InteractionState.IDLE
            and has_hand
        ):
            self._grab_hand(hand, hand_x, hand_y)
            return

        # ── PINCH while GRABBED: follow ──

        if (
            gesture == "PINCH"
            and hand.state == InteractionState.GRABBED
            and has_hand
        ):
            hand.frozen = False
            return

        # ── OPEN_PALM while GRABBED: release ──

        if (
            gesture == "OPEN_PALM"
            and hand.state == InteractionState.GRABBED
        ):
            hand.state = InteractionState.IDLE
            hand.frozen = False
            return

        # ── Everything else: freeze (stay in current state) ──

        if hand.state == InteractionState.GRABBED:
            hand.frozen = True

    def _grab_hand(
        self, hand: PerHandState, hand_x: float, hand_y: float
    ) -> None:
        """Enter GRABBED state for a single hand."""
        hand.offset.dx = self._sphere.x - hand_x
        hand.offset.dy = self._sphere.y - hand_y
        hand.state = InteractionState.GRABBED

    def _update_single_hand(self, hand: PerHandState) -> None:
        """Update sphere position for single-hand grab (V1.4 behavior).

        Only captures a new offset when transitioning from two-hand
        to single-hand mode. Otherwise preserves the original offset.
        """
        if self._was_two_hand:
            # Transitioning from two-hand to single-hand: capture new offset
            if hand.hand is not None:
                hand.offset.dx = self._sphere.x - hand.hand.x
                hand.offset.dy = self._sphere.y - hand.hand.y
            self._reset_two_hand_tracking()
            self._was_two_hand = False

        if not hand.frozen and hand.hand is not None:
            self._sphere.x = hand.hand.x + hand.offset.dx
            self._sphere.y = hand.hand.y + hand.offset.dy

    def _update_two_hand(self) -> None:
        """Update sphere for two-hand cooperative grab.

        When one hand is frozen, only the non-frozen hand moves
        the sphere. When both are frozen, sphere stays put.
        """
        left = self._hands[HandLabel.LEFT]
        right = self._hands[HandLabel.RIGHT]

        # If both hands are frozen, don't move anything
        if left.frozen and right.frozen:
            return

        lx = left.hand.x if left.hand else 0.0
        ly = left.hand.y if left.hand else 0.0
        rx = right.hand.x if right.hand else 0.0
        ry = right.hand.y if right.hand else 0.0

        # When one hand is frozen, use the midpoint that
        # accounts for the frozen hand staying put.
        # For distance/angle, use current positions regardless.
        if left.frozen:
            midpoint_x = rx
            midpoint_y = ry
        elif right.frozen:
            midpoint_x = lx
            midpoint_y = ly
        else:
            midpoint_x = (lx + rx) / 2.0
            midpoint_y = (ly + ry) / 2.0

        current_distance = math.sqrt(
            (rx - lx) ** 2 + (ry - ly) ** 2
        )
        current_angle = math.atan2(ry - ly, rx - lx)

        if self._initial_distance is None:
            self._two_hand_offset.dx = self._sphere.x - midpoint_x
            self._two_hand_offset.dy = self._sphere.y - midpoint_y
            self._initial_distance = current_distance
            self._initial_angle = current_angle

        self._sphere.x = midpoint_x + self._two_hand_offset.dx
        self._sphere.y = midpoint_y + self._two_hand_offset.dy

        # Scale: ratio of current to initial distance
        if self._initial_distance > 1e-6:
            self._sphere.scale = max(
                0.25, min(4.0, current_distance / self._initial_distance)
            )

        # Rotation: delta from initial angle
        self._sphere.rotation = current_angle - self._initial_angle

        self._was_two_hand = True

    def _reset_two_hand_tracking(self) -> None:
        """Reset two-hand distance/angle tracking."""
        self._initial_distance = None
        self._initial_angle = None
        self._sphere.scale = 1.0
        self._sphere.rotation = 0.0

    def _result(self) -> TwoHandResult:
        """Build the current frame result."""
        left = self._hands[HandLabel.LEFT]
        right = self._hands[HandLabel.RIGHT]

        any_grabbed = (
            left.state == InteractionState.GRABBED
            or right.state == InteractionState.GRABBED
        )
        both_grabbed = (
            left.state == InteractionState.GRABBED
            and right.state == InteractionState.GRABBED
        )

        if both_grabbed:
            combined = "TWO_HAND"
        elif any_grabbed:
            combined = "GRABBED"
        else:
            combined = "IDLE"

        return TwoHandResult(
            sphere_position=SphereStateExtended(
                x=self._sphere.x,
                y=self._sphere.y,
                scale=self._sphere.scale,
                rotation=self._sphere.rotation,
            ),
            interaction_state=combined,
            left_state=left.state,
            right_state=right.state,
            left_hand=(
                HandPosition(x=left.hand.x, y=left.hand.y)
                if left.hand
                else None
            ),
            right_hand=(
                HandPosition(x=right.hand.x, y=right.hand.y)
                if right.hand
                else None
            ),
        )
