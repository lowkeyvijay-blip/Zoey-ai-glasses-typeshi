"""V1.9 Abstract LLM interface.

Optional injectable interface for LLM-powered intent resolution.
The default implementation returns no intents — the system works
fully without an LLM.

Future implementations can plug in:
  - Local model inference
  - Cloud API calls
  - Hybrid rule + LLM resolution
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.intent.types import Intent
from backend.interaction.events import InteractionEvent
from backend.scene.object_interaction import ObjectInteractionEvent
from backend.scene.scene import Scene


class LLMInterface(ABC):
    """Abstract base for LLM-backed intent resolution.

    Implementations receive the current event stream and scene
    state, and may return additional intents that the rule-based
    engine would not produce.
    """

    @abstractmethod
    def suggest_intents(
        self,
        events: List[InteractionEvent],
        obj_events: List[ObjectInteractionEvent],
        scene: Scene,
        timestamp: int = 0,
    ) -> List[Intent]:
        """Suggest additional intents based on events and scene.

        Args:
            events: Controller-level events this frame.
            obj_events: Object-level events this frame.
            scene: Current scene state.
            timestamp: Current frame number.

        Returns:
            Additional intents to merge into the pipeline.
            May be empty.
        """
        ...


class NullLLM(LLMInterface):
    """Default no-op LLM. Returns no intents.

    Use this when no LLM is configured — the system works
    entirely on rule-based intent resolution.
    """

    def suggest_intents(
        self,
        events: List[InteractionEvent],
        obj_events: List[ObjectInteractionEvent],
        scene: Scene,
        timestamp: int = 0,
    ) -> List[Intent]:
        return []
