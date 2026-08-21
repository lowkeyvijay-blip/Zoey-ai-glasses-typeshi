"""V1.9 Action engine.

Consumes typed Intents, produces Actions, and mutates the Scene.
The ActionEngine is the single point of scene mutation — all
state changes flow through here.

No business logic lives in main.py.
"""

from __future__ import annotations

from typing import List, Optional

from backend.intent.types import Intent, IntentType
from backend.action.types import Action, ActionType
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectState


class ActionEngine:
    """Translates intents into actions and applies them to the Scene.

    The ActionEngine is the authority for scene mutations.
    It receives intents from the IntentEngine and produces
    observable actions that can be logged, replayed, or sent
    to the frontend.
    """

    def __init__(self) -> None:
        self._pending: List[Action] = []

    @property
    def pending_actions(self) -> List[Action]:
        return list(self._pending)

    def process_intents(
        self, intents: List[Intent], scene: Scene
    ) -> List[Action]:
        """Translate intents into actions and apply them.

        Args:
            intents: Intents from the IntentEngine.
            scene: The scene to mutate.

        Returns:
            Actions that were produced and applied.
        """
        self._pending.clear()
        actions: List[Action] = []

        for intent in intents:
            action = self._intent_to_action(intent, scene)
            if action is not None:
                self._apply(action, scene)
                actions.append(action)
                self._pending.append(action)

        return actions

    def _intent_to_action(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        """Convert a single intent to an action (may return None)."""
        handlers = {
            IntentType.MOVE: self._handle_move,
            IntentType.GRAB: self._handle_grab,
            IntentType.RELEASE: self._handle_release,
            IntentType.ROTATE: self._handle_rotate,
            IntentType.SCALE: self._handle_scale,
            IntentType.SELECT: self._handle_select,
            IntentType.CLICK: self._handle_click,
            IntentType.HOVER: self._handle_hover,
            IntentType.CANCEL: self._handle_cancel,
            IntentType.NAVIGATE: self._handle_navigate,
        }

        handler = handlers.get(intent.intent_type)
        if handler is None:
            return None
        return handler(intent, scene)

    def _apply(self, action: Action, scene: Scene) -> None:
        """Apply a single action to the scene."""
        method_map = {
            ActionType.MOVE_OBJECT: self._apply_move,
            ActionType.ROTATE_OBJECT: self._apply_rotate,
            ActionType.SCALE_OBJECT: self._apply_scale,
            ActionType.SELECT_OBJECT: self._apply_select,
            ActionType.OPEN_PANEL: self._apply_open_panel,
            ActionType.CLOSE_PANEL: self._apply_close_panel,
            ActionType.NAVIGATE: self._apply_navigate,
        }

        apply_fn = method_map.get(action.action_type)
        if apply_fn is not None:
            apply_fn(action, scene)

    # ── Intent → Action translators ───────────────

    def _handle_move(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        if scene.get_object(intent.target_object_id or "") is None:
            return None
        return Action(
            action_type=ActionType.MOVE_OBJECT,
            target_object_id=intent.target_object_id,
            dx=intent.delta_x,
            dy=intent.delta_y,
            dz=intent.delta_z,
        )

    def _handle_grab(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        obj = scene.get_object(intent.target_object_id or "")
        if obj is None:
            return None
        if obj.state == ObjectState.GRABBED:
            return None
        return Action(
            action_type=ActionType.SELECT_OBJECT,
            target_object_id=intent.target_object_id,
        )

    def _handle_release(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        obj = scene.get_object(intent.target_object_id or "")
        if obj is None:
            return None
        return Action(
            action_type=ActionType.SELECT_OBJECT,
            target_object_id=intent.target_object_id,
        )

    def _handle_rotate(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        return Action(
            action_type=ActionType.ROTATE_OBJECT,
            target_object_id=intent.target_object_id,
            rotation_delta=intent.rotation_delta,
        )

    def _handle_scale(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        return Action(
            action_type=ActionType.SCALE_OBJECT,
            target_object_id=intent.target_object_id,
            scale_factor=intent.scale_factor,
        )

    def _handle_select(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        return Action(
            action_type=ActionType.SELECT_OBJECT,
            target_object_id=intent.target_object_id,
        )

    def _handle_click(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        return Action(
            action_type=ActionType.SELECT_OBJECT,
            target_object_id=intent.target_object_id,
        )

    def _handle_hover(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        obj = scene.get_object(intent.target_object_id or "")
        if obj is None:
            return None
        if obj.state == ObjectState.DEFAULT:
            return Action(
                action_type=ActionType.SELECT_OBJECT,
                target_object_id=intent.target_object_id,
            )
        return None

    def _handle_cancel(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        obj = scene.get_object(intent.target_object_id or "")
        if obj is None:
            return None
        return Action(
            action_type=ActionType.SELECT_OBJECT,
            target_object_id=intent.target_object_id,
        )

    def _handle_navigate(
        self, intent: Intent, scene: Scene
    ) -> Optional[Action]:
        return Action(
            action_type=ActionType.NAVIGATE,
            target_object_id=intent.target_object_id,
        )

    # ── Action appliers ───────────────────────────

    def _apply_move(self, action: Action, scene: Scene) -> None:
        scene.update_object(
            action.target_object_id,
            x=action.dx,
            y=action.dy,
            z=action.dz,
        )

    def _apply_rotate(self, action: Action, scene: Scene) -> None:
        obj = scene.get_object(action.target_object_id or "")
        if obj:
            scene.update_object(
                action.target_object_id,
                rotation=obj.rotation + action.rotation_delta,
            )

    def _apply_scale(self, action: Action, scene: Scene) -> None:
        obj = scene.get_object(action.target_object_id or "")
        if obj:
            scene.update_object(
                action.target_object_id,
                scale=obj.scale * action.scale_factor,
            )

    def _apply_select(self, action: Action, scene: Scene) -> None:
        obj = scene.get_object(action.target_object_id or "")
        if obj and obj.state == ObjectState.DEFAULT:
            scene.update_object(
                action.target_object_id,
                state=ObjectState.SELECTED,
            )

    def _apply_open_panel(self, action: Action, scene: Scene) -> None:
        obj = scene.get_object(action.target_object_id or "")
        if obj:
            scene.update_object(
                action.target_object_id,
                state=ObjectState.SELECTED,
            )

    def _apply_close_panel(self, action: Action, scene: Scene) -> None:
        obj = scene.get_object(action.target_object_id or "")
        if obj:
            scene.update_object(
                action.target_object_id,
                state=ObjectState.DEFAULT,
            )

    def _apply_navigate(self, action: Action, scene: Scene) -> None:
        pass
