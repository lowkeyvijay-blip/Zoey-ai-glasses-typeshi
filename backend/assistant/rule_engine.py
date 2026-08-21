"""V2.0 Rule-based assistant.

Works WITHOUT any LLM. Interprets spatial context using
deterministic rules to produce assistant commands.

This is the default assistant — the system works fully
without an LLM.
"""

from __future__ import annotations

from typing import List, Optional

from backend.assistant.interface import (
    AssistantCommand,
    AssistantInterface,
    AssistantResponse,
)
from backend.scene.spatial_object import ObjectType


class RuleBasedAssistant(AssistantInterface):
    """Deterministic rule-based spatial assistant.

    Translates interaction state + gesture into high-level
    commands using simple rules. No AI required.
    """

    def __init__(self, scene=None) -> None:
        self._scene = scene

    def set_scene(self, scene) -> None:
        """Set the scene reference for object type lookups."""
        self._scene = scene

    def interpret(
        self,
        interaction_state: str,
        hovered_object_id: Optional[str] = None,
        selected_object_id: Optional[str] = None,
        gesture: str = "NO_HAND",
        hand_label: Optional[str] = None,
    ) -> AssistantResponse:
        """Interpret spatial context into commands."""
        obj_type = self._get_object_type(hovered_object_id)

        if interaction_state == "GRABBED" and gesture == "OPEN_PALM":
            return AssistantResponse(
                commands=[AssistantCommand.RELEASE],
                target_object_id=selected_object_id,
                message="Releasing object",
            )

        if interaction_state == "GRABBED":
            return AssistantResponse(
                commands=[AssistantCommand.GRAB],
                target_object_id=hovered_object_id or selected_object_id,
                message="Object grabbed",
            )

        if gesture == "PINCH" and hovered_object_id:
            if obj_type == ObjectType.BUTTON:
                return AssistantResponse(
                    commands=[AssistantCommand.CLICK, AssistantCommand.NAVIGATE],
                    target_object_id=hovered_object_id,
                    message="Button clicked",
                )
            if obj_type == ObjectType.PANEL:
                return AssistantResponse(
                    commands=[AssistantCommand.CLICK, AssistantCommand.SELECT],
                    target_object_id=hovered_object_id,
                    message="Panel selected",
                )
            return AssistantResponse(
                commands=[AssistantCommand.GRAB],
                target_object_id=hovered_object_id,
                message="Grabbing object",
            )

        if hovered_object_id:
            return AssistantResponse(
                commands=[AssistantCommand.SELECT],
                target_object_id=hovered_object_id,
                message="Hovering object",
            )

        return AssistantResponse(
            commands=[],
            message="Idle",
        )

    def _get_object_type(self, obj_id: Optional[str]) -> Optional[ObjectType]:
        if self._scene is None or obj_id is None:
            return None
        obj = self._scene.get_object(obj_id)
        return obj.object_type if obj else None
