"""Interaction event detector for V1.5.

Observes the controller's state transitions and gesture inputs
to emit typed InteractionEvents. Does NOT modify the controller
or its behavior — purely observational.

Detects:
  - GRAB / RELEASE (state transitions)
  - CLICK (quick grab+release within frame window)
  - DOUBLE_CLICK (two clicks within frame window)
  - FREEZE / RESUME (non-PINCH while grabbed)
"""

from __future__ import annotations

from typing import List, Optional

from backend.interaction.controller import (
    InteractionState,
    SpatialInteractionController,
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
