"""Interaction event detector for V1.5/V1.6.

Observes the controller's state transitions and gesture inputs
to emit typed InteractionEvents. Does NOT modify the controller
or its behavior — purely observational.

Detects:
  - GRAB / RELEASE (state transitions)
  - CLICK (quick grab+release within frame window)
  - DOUBLE_CLICK (two clicks within frame window)
  - FREEZE / RESUME (non-PINCH while grabbed)

V1.6: TwoHandEventDetector for per-hand event tracking.
"""

from __future__ import annotations

from typing import List, Optional

from backend.interaction.controller import (
    HandLabel,
    InteractionState,
    SpatialInteractionController,
    TwoHandController,
    TwoHandResult,
)
from backend.interaction.debouncer import Debouncer
from backend.interaction.events import EventType, InteractionEvent


class EventDetector:
    """Observes controller state and emits interaction events.

    Each WebSocket session should have its own EventDetector.
    The detector is purely deterministic — no I/O, no global state.

    Args:
        click_window: Max frames from GRAB to RELEASE for a click.
        double_click_window: Max frames between two clicks for
                             a double-click.
    """

    def __init__(
        self,
        click_window: int = 12,
        double_click_window: int = 40,
    ) -> None:
        self._frame: int = 0
        self._click_window = click_window
        self._double_click_window = double_click_window

        # State tracking
        self._was_grabbed: bool = False
        self._was_frozen: bool = False
        self._grab_start_frame: Optional[int] = None
        self._last_click_frame: Optional[int] = None

    @property
    def frame(self) -> int:
        return self._frame

    def process(
        self,
        gesture: str,
        controller: SpatialInteractionController,
        hand_x: Optional[float] = None,
        hand_y: Optional[float] = None,
    ) -> List[InteractionEvent]:
        """Process one frame and return any events detected.

        Args:
            gesture: The smoothed gesture label.
            controller: The interaction controller (to read state).
            hand_x: Normalized hand X. None if no hand.
            hand_y: Normalized hand Y. None if no hand.

        Returns:
            List of events detected in this frame (may be empty).
        """
        self._frame += 1
        events: List[InteractionEvent] = []
        current_state = controller.state
        hx = hand_x if hand_x is not None else 0.0
        hy = hand_y if hand_y is not None else 0.0

        is_grabbed = current_state == InteractionState.GRABBED
        is_idle = current_state == InteractionState.IDLE

        # ── GRAB detection ──

        if is_grabbed and not self._was_grabbed:
            events.append(
                InteractionEvent(
                    event_type=EventType.GRAB,
                    timestamp=self._frame,
                    hand_x=hx,
                    hand_y=hy,
                )
            )
            self._grab_start_frame = self._frame

        # ── RELEASE detection ──

        if is_idle and self._was_grabbed:
            events.append(
                InteractionEvent(
                    event_type=EventType.RELEASE,
                    timestamp=self._frame,
                    hand_x=hx,
                    hand_y=hy,
                )
            )

            # ── CLICK detection ──

            if self._grab_start_frame is not None:
                grab_duration = (
                    self._frame - self._grab_start_frame
                )

                if grab_duration <= self._click_window:
                    events.append(
                        InteractionEvent(
                            event_type=EventType.CLICK,
                            timestamp=self._frame,
                            hand_x=hx,
                            hand_y=hy,
                        )
                    )

                    # ── DOUBLE_CLICK detection ──

                    if (
                        self._last_click_frame is not None
                        and (
                            self._frame - self._last_click_frame
                            <= self._double_click_window
                        )
                    ):
                        events.append(
                            InteractionEvent(
                                event_type=EventType.DOUBLE_CLICK,
                                timestamp=self._frame,
                                hand_x=hx,
                                hand_y=hy,
                            )
                        )

                    self._last_click_frame = self._frame

            self._grab_start_frame = None

        # ── FREEZE / RESUME detection ──

        currently_frozen = (
            is_grabbed and gesture != "PINCH"
        )

        if currently_frozen and not self._was_frozen:
            events.append(
                InteractionEvent(
                    event_type=EventType.FREEZE,
                    timestamp=self._frame,
                    hand_x=hx,
                    hand_y=hy,
                )
            )

        if (
            not currently_frozen
            and self._was_frozen
            and is_grabbed
        ):
            events.append(
                InteractionEvent(
                    event_type=EventType.RESUME,
                    timestamp=self._frame,
                    hand_x=hx,
                    hand_y=hy,
                )
            )

        # ── Update tracking state ──

        self._was_grabbed = is_grabbed
        self._was_frozen = currently_frozen

        return events


# ─────────────────────────────────────────────────
# V1.6: Two-Hand Event Detector
# ─────────────────────────────────────────────────


class TwoHandEventDetector:
    """Per-hand event detector for two-hand interaction.

    Tracks each hand independently and emits events with
    hand_label attribution. Does NOT modify the controller.

    Args:
        click_window: Max frames from GRAB to RELEASE for a click.
        double_click_window: Max frames between two clicks for
                             a double-click.
    """

    def __init__(
        self,
        click_window: int = 12,
        double_click_window: int = 40,
    ) -> None:
        self._frame: int = 0
        self._click_window = click_window
        self._double_click_window = double_click_window

        # Per-hand tracking
        self._per_hand: dict[str, dict] = {}

    def _get_hand_state(self, label: str) -> dict:
        """Get or initialize per-hand tracking state."""
        if label not in self._per_hand:
            self._per_hand[label] = {
                "was_grabbed": False,
                "was_frozen": False,
                "grab_start_frame": None,
                "last_click_frame": None,
            }
        return self._per_hand[label]

    @property
    def frame(self) -> int:
        return self._frame

    def process(
        self,
        result: TwoHandResult,
        left_gesture: str = "NO_HAND",
        right_gesture: str = "NO_HAND",
    ) -> List[InteractionEvent]:
        """Process one frame and return per-hand events.

        Args:
            result: The TwoHandResult from the controller.
            left_gesture: Left hand gesture for this frame.
            right_gesture: Right hand gesture for this frame.

        Returns:
            List of events with hand_label attribution.
        """
        self._frame += 1
        events: List[InteractionEvent] = []

        gestures = {
            "LEFT": left_gesture,
            "RIGHT": right_gesture,
        }
        states = {
            "LEFT": result.left_state,
            "RIGHT": result.right_state,
        }
        hands = {
            "LEFT": result.left_hand,
            "RIGHT": result.right_hand,
        }

        for label in ("LEFT", "RIGHT"):
            hs = self._get_hand_state(label)
            current_state = states[label]
            gesture = gestures[label]
            hand = hands[label]

            hx = hand.x if hand else 0.0
            hy = hand.y if hand else 0.0

            is_grabbed = current_state == InteractionState.GRABBED
            is_idle = current_state == InteractionState.IDLE

            # ── GRAB detection ──

            if is_grabbed and not hs["was_grabbed"]:
                events.append(
                    InteractionEvent(
                        event_type=EventType.GRAB,
                        timestamp=self._frame,
                        hand_x=hx,
                        hand_y=hy,
                        hand_label=label,
                    )
                )
                hs["grab_start_frame"] = self._frame

            # ── RELEASE detection ──

            if is_idle and hs["was_grabbed"]:
                events.append(
                    InteractionEvent(
                        event_type=EventType.RELEASE,
                        timestamp=self._frame,
                        hand_x=hx,
                        hand_y=hy,
                        hand_label=label,
                    )
                )

                # ── CLICK detection ──

                if hs["grab_start_frame"] is not None:
                    grab_duration = (
                        self._frame - hs["grab_start_frame"]
                    )

                    if grab_duration <= self._click_window:
                        events.append(
                            InteractionEvent(
                                event_type=EventType.CLICK,
                                timestamp=self._frame,
                                hand_x=hx,
                                hand_y=hy,
                                hand_label=label,
                            )
                        )

                        # ── DOUBLE_CLICK detection ──

                        if (
                            hs["last_click_frame"] is not None
                            and (
                                self._frame - hs["last_click_frame"]
                                <= self._double_click_window
                            )
                        ):
                            events.append(
                                InteractionEvent(
                                    event_type=EventType.DOUBLE_CLICK,
                                    timestamp=self._frame,
                                    hand_x=hx,
                                    hand_y=hy,
                                    hand_label=label,
                                )
                            )

                        hs["last_click_frame"] = self._frame

                hs["grab_start_frame"] = None

            # ── FREEZE / RESUME detection ──

            currently_frozen = (
                is_grabbed and gesture != "PINCH"
            )

            if currently_frozen and not hs["was_frozen"]:
                events.append(
                    InteractionEvent(
                        event_type=EventType.FREEZE,
                        timestamp=self._frame,
                        hand_x=hx,
                        hand_y=hy,
                        hand_label=label,
                    )
                )

            if (
                not currently_frozen
                and hs["was_frozen"]
                and is_grabbed
            ):
                events.append(
                    InteractionEvent(
                        event_type=EventType.RESUME,
                        timestamp=self._frame,
                        hand_x=hx,
                        hand_y=hy,
                        hand_label=label,
                    )
                )

            # ── Update tracking state ──

            hs["was_grabbed"] = is_grabbed
            hs["was_frozen"] = currently_frozen

        return events
