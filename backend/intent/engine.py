"""V1.9 Intent engine.

Translates interaction events (from EventDetector and
ObjectInteractionManager) into typed Intents. This is the
rule-based default — the optional LLM can augment/override.

Architecture:
  Events + Controller State + Object States
        ↓
    IntentEngine.resolve()
        ↓
    List[Intent]
        ↓
    ActionEngine.execute()
"""

from __future__ import annotations

from typing import List, Optional

from backend.intent.types import Intent, IntentType
from backend.interaction.events import EventType, InteractionEvent
from backend.scene.object_interaction import ObjectInteractionEvent
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectType


class IntentEngine:
    """Rule-based intent resolver.

    Translates raw interaction events into typed intents.
    Optionally consults an LLM interface for ambiguity
    resolution or natural-language commands.
    """

    def __init__(self, llm: Optional["LLMInterface"] = None) -> None:
        from backend.intent.llm_interface import LLMInterface
        self._llm: Optional[LLMInterface] = llm

    def resolve(
        self,
        controller_events: List[InteractionEvent],
        obj_events: List[ObjectInteractionEvent],
        interaction_state: str,
        scene: Scene,
        timestamp: int = 0,
    ) -> List[Intent]:
        """Translate events into typed intents.

        Args:
            controller_events: Events from EventDetector (primary sphere).
            obj_events: Events from ObjectInteractionManager (scene objects).
            interaction_state: Current state string from TwoHandController.
            scene: The scene registry for object lookups.
            timestamp: Current frame timestamp.

        Returns:
            List of resolved intents.
        """
        intents: List[Intent] = []

        for ev in controller_events:
            intents.extend(self._resolve_controller_event(ev))

        for oe in obj_events:
            intents.extend(self._resolve_object_event(oe, scene))

        if self._llm is not None:
            llm_intents = self._llm.suggest_intents(
                events=controller_events + [],
                obj_events=obj_events,
                scene=scene,
                timestamp=timestamp,
            )
            intents.extend(llm_intents)

        return intents

    def _resolve_controller_event(
        self, ev: InteractionEvent
    ) -> List[Intent]:
        """Translate a controller-level event to intent(s)."""
        mapping = {
            EventType.GRAB: IntentType.GRAB,
            EventType.RELEASE: IntentType.RELEASE,
            EventType.CLICK: IntentType.CLICK,
            EventType.DOUBLE_CLICK: IntentType.CLICK,
            EventType.FREEZE: IntentType.CANCEL,
            EventType.RESUME: IntentType.MOVE,
        }

        intent_type = mapping.get(ev.event_type)
        if intent_type is None:
            return []

        return [
            Intent(
                intent_type=intent_type,
                target_object_id="sphere",
                hand_label=ev.hand_label,
                x=ev.hand_x,
                y=ev.hand_y,
                z=ev.hand_z,
            )
        ]

    def _resolve_object_event(
        self, oe: ObjectInteractionEvent, scene: Scene
    ) -> List[Intent]:
        """Translate an object-level event to intent(s)."""
        type_map = {
            "CLICK": IntentType.CLICK,
            "GRAB": IntentType.GRAB,
            "RELEASE": IntentType.RELEASE,
        }

        intent_type = type_map.get(oe.event_type)
        if intent_type is None:
            return []

        intent = Intent(
            intent_type=intent_type,
            target_object_id=oe.object_id,
            hand_label=oe.hand_label,
            x=oe.x,
            y=oe.y,
            z=oe.z,
        )

        intents = [intent]

        if (
            intent_type == IntentType.CLICK
            and oe.object_id
        ):
            obj = scene.get_object(oe.object_id)
            if obj and obj.object_type == ObjectType.BUTTON:
                intents.append(
                    Intent(
                        intent_type=IntentType.NAVIGATE,
                        target_object_id=oe.object_id,
                        hand_label=oe.hand_label,
                        x=oe.x,
                        y=oe.y,
                        z=oe.z,
                    )
                )
            elif obj and obj.object_type == ObjectType.PANEL:
                intents.append(
                    Intent(
                        intent_type=IntentType.SELECT,
                        target_object_id=oe.object_id,
                        hand_label=oe.hand_label,
                        x=oe.x,
                        y=oe.y,
                        z=oe.z,
                    )
                )

        return intents
