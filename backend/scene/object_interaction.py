"""Object-level interaction manager for V1.8.

Handles hover, grab, release, and click on spatial objects
EXCLUDING the primary sphere (which is managed by
SpatialInteractionController).

Per-hand state machine:
  IDLE -> HOVERED -> SELECTED -> GRABBED -> IDLE

Two-hand conflict: an object grabbed_by one hand cannot be
grabbed by the other.

Click detection: short pinch-duration (<= CLICK_GRAB_THRESHOLD
frames) at ~same position generates a CLICK event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectState


CLICK_GRAB_THRESHOLD = 4
CLICK_POSITION_TOLERANCE = 0.05


@dataclass
class HandState:
    """Interaction state for one hand."""

    hand_label: str
    state: str = "IDLE"
    target_object_id: Optional[str] = None
    grab_offset_x: float = 0.0
    grab_offset_y: float = 0.0
    grab_offset_z: float = 0.0
    pinch_start_x: float = 0.0
    pinch_start_y: float = 0.0
    pinch_start_z: float = 0.0
    pinch_frame_count: int = 0
    is_pinching: bool = False


@dataclass
class ObjectInteractionEvent:
    """An event emitted by the object interaction manager."""

    event_type: str
    timestamp: int
    hand_label: str
    object_id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ObjectInteractionManager:
    """Manages per-object hover, grab, release, and click.

    Excludes the primary sphere — that continues to be driven
    by SpatialInteractionController.
    """

    def __init__(
        self,
        exclude_ids: Optional[Set[str]] = None,
    ) -> None:
        self._exclude_ids = exclude_ids or set()
        self._hand_states: dict[str, HandState] = {}
        self._timestamp: int = 0
        self._event_log: List[ObjectInteractionEvent] = []

    @property
    def event_log(self) -> List[ObjectInteractionEvent]:
        return list(self._event_log)

    def get_hand_state(self, hand_label: str) -> Optional[HandState]:
        return self._hand_states.get(hand_label)

    def clear_hand(self, hand_label: str) -> None:
        hs = self._hand_states.pop(hand_label, None)
        if hs is not None:
            hs.target_object_id = None
            hs.state = "IDLE"

    def process_frame(
        self,
        scene: Scene,
        left_gesture: Optional[str] = None,
        left_x: Optional[float] = None,
        left_y: Optional[float] = None,
        left_z: Optional[float] = None,
        right_gesture: Optional[str] = None,
        right_x: Optional[float] = None,
        right_y: Optional[float] = None,
        right_z: Optional[float] = None,
        timestamp: int = 0,
    ) -> List[ObjectInteractionEvent]:
        """Run one frame of object interaction.

        Returns events generated this frame (CLICK, GRAB, RELEASE).
        """
        self._timestamp = timestamp
        self._event_log.clear()

        for label, gx, gy, gz, gesture in [
            ("LEFT", left_x, left_y, left_z, left_gesture),
            ("RIGHT", right_x, right_y, right_z, right_gesture),
        ]:
            self._process_hand(scene, label, gx, gy, gz, gesture)

        return list(self._event_log)

    def _get_or_create_hand(self, label: str) -> HandState:
        if label not in self._hand_states:
            self._hand_states[label] = HandState(hand_label=label)
        return self._hand_states[label]

    def _is_excluded(self, obj_id: str) -> bool:
        return obj_id in self._exclude_ids

    def _find_hovered_object(
        self, scene: Scene, x: float, y: float, z: float
    ) -> Optional[str]:
        """Hit-test against scene, returning closest non-excluded object."""
        closest_id = None
        closest_dist = float("inf")

        for oid, obj in scene.objects.items():
            if self._is_excluded(oid):
                continue
            dx = obj.x - x
            dy = obj.y - y
            dz = obj.z - z
            dist = (dx * dx + dy * dy + dz * dz) ** 0.5
            effective_radius = obj.hit_radius * obj.scale
            if dist <= effective_radius and dist < closest_dist:
                closest_id = oid
                closest_dist = dist

        return closest_id

    def _is_other_hand_targeting(
        self, scene: Scene, obj_id: str, exclude_label: str
    ) -> bool:
        """Check if any hand other than exclude_label targets this object."""
        for label, hs in self._hand_states.items():
            if label != exclude_label and hs.target_object_id == obj_id:
                return True
        return False

    def _clear_own_target_state(
        self, scene: Scene, hs: HandState
    ) -> None:
        """Clear scene state for this hand's previous target, if no other
        hand is still targeting it."""
        if not hs.target_object_id or self._is_excluded(hs.target_object_id):
            return
        if self._is_other_hand_targeting(
            scene, hs.target_object_id, hs.hand_label
        ):
            return
        obj = scene.get_object(hs.target_object_id)
        if obj is None:
            return
        if obj.state == ObjectState.GRABBED and obj.grabbed_by != hs.hand_label:
            return
        if obj.state in (ObjectState.HOVERED, ObjectState.SELECTED):
            obj.state = ObjectState.DEFAULT

    def _process_hand(
        self,
        scene: Scene,
        hand_label: str,
        x: Optional[float],
        y: Optional[float],
        z: Optional[float],
        gesture: Optional[str],
    ) -> None:
        is_pinching = gesture == "PINCH"
        hand_lost = gesture == "NO_HAND" or x is None

        hs = self._get_or_create_hand(hand_label)

        # ── Hand lost ────────────────────────────
        if hand_lost:
            if hs.state == "GRABBED" and hs.target_object_id:
                obj = scene.get_object(hs.target_object_id)
                if obj and not self._is_excluded(hs.target_object_id):
                    obj.state = ObjectState.DEFAULT
                    obj.grabbed_by = None
                    self._emit(
                        "RELEASE", scene, hs,
                        x or 0.0, y or 0.0, z or 0.0,
                    )
            elif hs.state in ("HOVERED", "SELECTED") and hs.target_object_id:
                self._clear_own_target_state(scene, hs)
            hs.state = "IDLE"
            hs.target_object_id = None
            hs.is_pinching = False
            hs.pinch_frame_count = 0
            return

        prev_pinching = hs.is_pinching
        hs.is_pinching = is_pinching

        # ── If grabbed, just move the object ─────
        if hs.state == "GRABBED" and hs.target_object_id:
            obj = scene.get_object(hs.target_object_id)
            if obj and obj.grabbed_by == hand_label:
                obj.x = x - hs.grab_offset_x
                obj.y = y - hs.grab_offset_y
                obj.z = z - hs.grab_offset_z
                # Check if released (pinch ended)
                if not is_pinching:
                    obj.state = ObjectState.DEFAULT
                    obj.grabbed_by = None
                    self._emit(
                        "RELEASE", scene, hs,
                        x, y, z,
                    )
                    hs.state = "IDLE"
                    hs.target_object_id = None
                return
            else:
                # Object was taken by another hand or removed
                hs.state = "IDLE"
                hs.target_object_id = None

        # ── Pinch → release transition ───────────
        if prev_pinching and not is_pinching:
            if hs.state in ("HOVERED", "SELECTED") and hs.target_object_id:
                if not self._is_excluded(hs.target_object_id):
                    obj = scene.get_object(hs.target_object_id)
                    if obj and hs.pinch_frame_count > 0:
                        if hs.pinch_frame_count <= CLICK_GRAB_THRESHOLD:
                            self._emit_click_at_position(
                                scene, hs,
                                hs.pinch_start_x,
                                hs.pinch_start_y,
                                hs.pinch_start_z,
                            )
                        else:
                            self._emit(
                                "RELEASE", scene, hs,
                                x, y, z,
                            )
                hs.state = "IDLE"
                hs.target_object_id = None
                hs.pinch_frame_count = 0

            # After handling release, fall through to hover detection below

        # ── Pinch start ──────────────────────────
        if is_pinching and not prev_pinching:
            hs.pinch_start_x = x
            hs.pinch_start_y = y
            hs.pinch_start_z = z
            hs.pinch_frame_count = 0

        if is_pinching:
            hs.pinch_frame_count += 1

        # ── Not pinching → hover detection ──────
        if not is_pinching:
            self._clear_own_target_state(scene, hs)

            hovered_id = self._find_hovered_object(scene, x, y, z)
            if hovered_id:
                obj = scene.get_object(hovered_id)
                if obj:
                    obj.state = ObjectState.HOVERED
                hs.state = "HOVERED"
                hs.target_object_id = hovered_id
            else:
                hs.state = "IDLE"
                hs.target_object_id = None
            return

        # ── Pinching while near an object ────────
        hovered_id = self._find_hovered_object(scene, x, y, z)

        if hovered_id and not self._is_excluded(hovered_id):
            obj = scene.get_object(hovered_id)
            if obj is None:
                hs.state = "IDLE"
                hs.target_object_id = None
                return

            # Two-hand conflict: another hand owns this object
            if obj.grabbed_by and obj.grabbed_by != hand_label:
                return

            if hs.pinch_frame_count <= CLICK_GRAB_THRESHOLD:
                # Short pinch → SELECTED
                obj.state = ObjectState.SELECTED
                hs.state = "HOVERED"
                hs.target_object_id = hovered_id
            else:
                # Long pinch → GRABBED
                was_already_grabbed = (
                    hs.state == "GRABBED" and hs.target_object_id == hovered_id
                )
                if not was_already_grabbed:
                    hs.state = "GRABBED"
                    hs.target_object_id = hovered_id
                    hs.grab_offset_x = x - obj.x
                    hs.grab_offset_y = y - obj.y
                    hs.grab_offset_z = z - obj.z
                    self._emit(
                        "GRAB", scene, hs,
                        x, y, z,
                    )
                obj.state = ObjectState.GRABBED
                obj.grabbed_by = hand_label
        else:
            # Pinching but not near any object
            if hs.state in ("HOVERED", "SELECTED") and hs.target_object_id:
                self._clear_own_target_state(scene, hs)
            hs.state = "IDLE"
            hs.target_object_id = None

    def _is_click(
        self,
        hs: HandState,
        x: float,
        y: float,
        z: float,
    ) -> bool:
        dx = x - hs.pinch_start_x
        dy = y - hs.pinch_start_y
        dz = z - hs.pinch_start_z
        dist = (dx * dx + dy * dy + dz * dz) ** 0.5
        return (
            hs.pinch_frame_count <= CLICK_GRAB_THRESHOLD
            and dist <= CLICK_POSITION_TOLERANCE
        )

    def _emit_click_at_position(
        self,
        scene: Scene,
        hs: HandState,
        x: float,
        y: float,
        z: float,
    ) -> None:
        """Emit a CLICK event and reset the target object's state."""
        self._emit("CLICK", scene, hs, x, y, z)

    def _emit(
        self,
        event_type: str,
        scene: Scene,
        hs: HandState,
        x: float,
        y: float,
        z: float,
    ) -> None:
        ev = ObjectInteractionEvent(
            event_type=event_type,
            timestamp=self._timestamp,
            hand_label=hs.hand_label,
            object_id=hs.target_object_id or "",
            x=x,
            y=y,
            z=z,
        )
        self._event_log.append(ev)

        if hs.target_object_id and not self._is_excluded(hs.target_object_id):
            obj = scene.get_object(hs.target_object_id)
            if obj and obj.state != ObjectState.GRABBED:
                obj.state = ObjectState.DEFAULT
            if obj:
                obj.grabbed_by = None
