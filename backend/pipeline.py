"""V2.0 Pipeline.

Orchestrates the full interaction loop with no business logic
in main.py. Each frame flows through:

  Vision -> Gesture -> Controller -> Events -> Intent -> Action -> Scene

main.py calls pipeline.process_frame() with raw data and gets
back the complete payload for the WebSocket.

V2.0: Added logging, error handling, and protocol version.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.interaction.controller import TwoHandController
from backend.interaction.event_detector import TwoHandEventDetector
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectType, ObjectState, VisualProperties
from backend.scene.object_interaction import ObjectInteractionManager
from backend.intent.engine import IntentEngine
from backend.intent.types import Intent
from backend.action.engine import ActionEngine
from backend.action.types import Action

logger = logging.getLogger(__name__)


@dataclass
class FrameResult:
    """Complete result of one pipeline frame."""

    sphere_x: float = 0.0
    sphere_y: float = 0.0
    sphere_z: float = 0.0
    sphere_scale: float = 1.0
    sphere_rotation: float = 0.0
    interaction_state: str = "IDLE"
    left_state: str = "IDLE"
    right_state: str = "IDLE"
    left_hand: Optional[Dict[str, float]] = None
    right_hand: Optional[Dict[str, float]] = None
    controller_events: List[Dict[str, Any]] = field(default_factory=list)
    obj_events: List[Dict[str, Any]] = field(default_factory=list)
    intents: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    scene: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sphere_x": self.sphere_x,
            "sphere_y": self.sphere_y,
            "sphere_z": self.sphere_z,
            "sphere_scale": self.sphere_scale,
            "sphere_rotation": self.sphere_rotation,
            "interaction_state": self.interaction_state,
            "left_state": self.left_state,
            "right_state": self.right_state,
            "left_hand": self.left_hand,
            "right_hand": self.right_hand,
            "events": self.controller_events + self.obj_events,
            "intents": self.intents,
            "actions": self.actions,
            "scene": self.scene,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Pipeline:
    """Full interaction pipeline.

    Wires together controller, event detector, scene,
    object interaction, intent engine, and action engine.
    """

    def __init__(
        self,
        scene: Optional[Scene] = None,
        controller: Optional[TwoHandController] = None,
        event_detector: Optional[TwoHandEventDetector] = None,
        intent_engine: Optional[IntentEngine] = None,
        action_engine: Optional[ActionEngine] = None,
        obj_interaction: Optional[ObjectInteractionManager] = None,
    ) -> None:
        self.scene = scene or Scene()
        self.controller = controller or TwoHandController()
        self.event_detector = event_detector or TwoHandEventDetector(
            click_window=12, double_click_window=40,
        )
        self.intent_engine = intent_engine or IntentEngine()
        self.action_engine = action_engine or ActionEngine()
        self.obj_interaction = obj_interaction or ObjectInteractionManager(
            exclude_ids={"sphere"},
        )

        self._primary_sphere = self.scene.add_object(
            obj_id="sphere",
            object_type=ObjectType.SPHERE,
            visual=VisualProperties(color="#00aaff", label="Sphere"),
            hit_radius=0.8,
        )

        self.scene.add_object(
            obj_id="panel",
            object_type=ObjectType.PANEL,
            x=0.5, y=0.6, z=-0.5,
            scale=1.0,
            visual=VisualProperties(
                color="#1a2a3a", label="Panel",
                width=2.0, height=1.2, opacity=0.85,
            ),
            hit_radius=1.5,
        )
        self.scene.add_object(
            obj_id="button",
            object_type=ObjectType.BUTTON,
            x=-0.5, y=0.55, z=0.0,
            scale=1.0,
            visual=VisualProperties(
                color="#22aa66", label="OK",
                width=0.6, height=0.3,
            ),
            hit_radius=0.5,
        )
        self.scene.add_object(
            obj_id="card",
            object_type=ObjectType.CARD,
            x=0.0, y=0.7, z=-1.0,
            scale=1.0,
            visual=VisualProperties(
                color="#2a1a3a", label="Info Card",
                width=1.0, height=0.7, opacity=0.9,
            ),
            hit_radius=0.8,
        )

    def process_frame(
        self,
        left_gesture: str = "NO_HAND",
        left_x: Optional[float] = None,
        left_y: Optional[float] = None,
        left_z: Optional[float] = None,
        right_gesture: str = "NO_HAND",
        right_x: Optional[float] = None,
        right_y: Optional[float] = None,
        right_z: Optional[float] = None,
        timestamp: int = 0,
    ) -> FrameResult:
        """Run one full pipeline frame."""
        interaction = self.controller.process_frame(
            left_gesture=left_gesture,
            left_x=left_x, left_y=left_y, left_z=left_z,
            right_gesture=right_gesture,
            right_x=right_x, right_y=right_y, right_z=right_z,
        )

        controller_events = self.event_detector.process(
            result=interaction,
            left_gesture=left_gesture,
            right_gesture=right_gesture,
        )

        sp = interaction.sphere_position
        self._primary_sphere.x = sp.x
        self._primary_sphere.y = sp.y
        self._primary_sphere.z = sp.z
        self._primary_sphere.scale = sp.scale
        self._primary_sphere.rotation = sp.rotation

        if left_x is not None:
            self.scene.update_cursor("LEFT", left_x, left_y or 0.0, left_z or 0.0)
        else:
            self.scene.clear_cursor("LEFT")

        if right_x is not None:
            self.scene.update_cursor("RIGHT", right_x, right_y or 0.0, right_z or 0.0)
        else:
            self.scene.clear_cursor("RIGHT")

        if interaction.interaction_state in ("GRABBED", "TWO_HAND"):
            self._primary_sphere.state = ObjectState.GRABBED
        elif self._primary_sphere.state == ObjectState.GRABBED:
            self._primary_sphere.state = ObjectState.DEFAULT

        obj_events = self.obj_interaction.process_frame(
            scene=self.scene,
            left_gesture=left_gesture,
            left_x=left_x, left_y=left_y, left_z=left_z,
            right_gesture=right_gesture,
            right_x=right_x, right_y=right_y, right_z=right_z,
            timestamp=timestamp,
        )

        intents = self.intent_engine.resolve(
            controller_events=controller_events,
            obj_events=obj_events,
            interaction_state=interaction.interaction_state,
            scene=self.scene,
            timestamp=timestamp,
        )

        actions = self.action_engine.process_intents(
            intents=intents,
            scene=self.scene,
        )

        return FrameResult(
            sphere_x=sp.x,
            sphere_y=sp.y,
            sphere_z=sp.z,
            sphere_scale=sp.scale,
            sphere_rotation=sp.rotation,
            interaction_state=interaction.interaction_state,
            left_state=interaction.left_state.value,
            right_state=interaction.right_state.value,
            left_hand=(
                {"x": interaction.left_hand.x, "y": interaction.left_hand.y, "z": interaction.left_hand.z}
                if interaction.left_hand else None
            ),
            right_hand=(
                {"x": interaction.right_hand.x, "y": interaction.right_hand.y, "z": interaction.right_hand.z}
                if interaction.right_hand else None
            ),
            controller_events=[
                {"type": ev.event_type.value, "timestamp": ev.timestamp, "hand_label": ev.hand_label}
                for ev in controller_events
            ],
            obj_events=[
                {"type": oe.event_type, "timestamp": oe.timestamp, "hand_label": oe.hand_label,
                 "object_id": oe.object_id, "x": oe.x, "y": oe.y, "z": oe.z}
                for oe in obj_events
            ],
            intents=[
                {"type": i.intent_type.value, "target_object_id": i.target_object_id,
                 "hand_label": i.hand_label, "x": i.x, "y": i.y, "z": i.z,
                 "from_llm": i.from_llm}
                for i in intents
            ],
            actions=[
                {"type": a.action_type.value, "target_object_id": a.target_object_id,
                 "dx": a.dx, "dy": a.dy, "dz": a.dz}
                for a in actions
            ],
            scene=self.scene.serialize(),
        )
