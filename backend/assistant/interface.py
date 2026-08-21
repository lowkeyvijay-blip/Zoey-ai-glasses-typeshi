"""V2.0 Assistant interface.

Abstract base class for spatial assistants. Implementations
interpret spatial context and intents. The default implementation
works without any LLM.

Future local LLM implementations can be injected without
modifying the spatial/scene/action systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class AssistantCommand(Enum):
    """High-level commands the assistant can emit."""
    SELECT = "SELECT"
    CLICK = "CLICK"
    GRAB = "GRAB"
    RELEASE = "RELEASE"
    MOVE = "MOVE"
    ROTATE = "ROTATE"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    CANCEL = "CANCEL"
    NAVIGATE = "NAVIGATE"


@dataclass(frozen=True)
class AssistantResponse:
    """Response from the assistant."""
    commands: List[AssistantCommand]
    target_object_id: Optional[str] = None
    message: str = ""


class AssistantInterface(ABC):
    """Abstract base for spatial assistants.

    Implementations receive spatial context and produce
    high-level commands that the pipeline translates to
    intents/actions.
    """

    @abstractmethod
    def interpret(
        self,
        interaction_state: str,
        hovered_object_id: Optional[str] = None,
        selected_object_id: Optional[str] = None,
        gesture: str = "NO_HAND",
        hand_label: Optional[str] = None,
    ) -> AssistantResponse:
        """Interpret the current spatial context.

        Args:
            interaction_state: Current interaction state.
            hovered_object_id: Object under cursor, if any.
            selected_object_id: Object currently selected, if any.
            gesture: Current gesture label.
            hand_label: Which hand ("LEFT"/"RIGHT"/None).

        Returns:
            AssistantResponse with commands.
        """
        ...
