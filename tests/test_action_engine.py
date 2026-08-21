"""Tests for V1.9 ActionEngine.

Covers:
  - Intent → Action translation
  - MOVE action applies delta to scene object
  - ROTATE action adds rotation delta
  - SCALE action multiplies scale
  - SELECT action sets state to SELECTED
  - NAVIGATE action (no-op on scene)
  - GRAB → SELECT_OBJECT
  - RELEASE → SELECT_OBJECT
  - CANCEL → SELECT_OBJECT
  - HOVER → SELECT_OBJECT if DEFAULT
  - No-op for missing objects
  - Action logging
"""

import pytest

from backend.intent.types import Intent, IntentType
from backend.action.types import Action, ActionType
from backend.action.engine import ActionEngine
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectType, ObjectState, VisualProperties


@pytest.fixture
def scene():
    s = Scene()
    s.add_object(
        obj_id="sphere",
        object_type=ObjectType.SPHERE,
        visual=VisualProperties(color="#00aaff"),
        hit_radius=0.8,
    )
    s.add_object(
        obj_id="panel",
        object_type=ObjectType.PANEL,
        x=0.5, y=0.6, z=-0.5,
        rotation=0.0,
        scale=1.0,
        visual=VisualProperties(color="#1a2a3a"),
        hit_radius=1.5,
    )
    s.add_object(
        obj_id="button",
        object_type=ObjectType.BUTTON,
        x=-0.5, y=0.55, z=0.0,
        scale=1.0,
        visual=VisualProperties(color="#22aa66"),
        hit_radius=0.5,
    )
    s.add_object(
        obj_id="card",
        object_type=ObjectType.CARD,
        x=0.0, y=0.7, z=-1.0,
        rotation=0.0,
        scale=2.0,
        visual=VisualProperties(color="#2a1a3a"),
        hit_radius=0.8,
    )
    return s


@pytest.fixture
def engine():
    return ActionEngine()


# ── MOVE ───────────────────────────────────────────


class TestMove:
    def test_move_intent_produces_action(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.MOVE,
            target_object_id="panel",
            delta_x=0.1,
            delta_y=0.2,
            delta_z=0.3,
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MOVE_OBJECT

    def test_move_updates_scene(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.MOVE,
            target_object_id="panel",
            delta_x=1.0,
            delta_y=2.0,
            delta_z=3.0,
        )
        engine.process_intents([intent], scene)
        panel = scene.get_object("panel")
        assert panel.x == 1.0
        assert panel.y == 2.0
        assert panel.z == 3.0

    def test_move_missing_object_no_crash(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.MOVE,
            target_object_id="nonexistent",
            delta_x=1.0,
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 0


# ── ROTATE ─────────────────────────────────────────


class TestRotate:
    def test_rotate_adds_delta(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.ROTATE,
            target_object_id="panel",
            rotation_delta=0.5,
        )
        engine.process_intents([intent], scene)
        panel = scene.get_object("panel")
        assert panel.rotation == pytest.approx(0.5)

    def test_rotate_cumulative(self, engine, scene):
        for _ in range(4):
            engine.process_intents(
                [Intent(
                    intent_type=IntentType.ROTATE,
                    target_object_id="panel",
                    rotation_delta=0.5,
                )],
                scene,
            )
        panel = scene.get_object("panel")
        assert panel.rotation == pytest.approx(2.0)


# ── SCALE ──────────────────────────────────────────


class TestScale:
    def test_scale_multiplies(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.SCALE,
            target_object_id="card",
            scale_factor=1.5,
        )
        engine.process_intents([intent], scene)
        card = scene.get_object("card")
        assert card.scale == pytest.approx(3.0)

    def test_scale_cumulative(self, engine, scene):
        for _ in range(3):
            engine.process_intents(
                [Intent(
                    intent_type=IntentType.SCALE,
                    target_object_id="card",
                    scale_factor=2.0,
                )],
                scene,
            )
        card = scene.get_object("card")
        assert card.scale == pytest.approx(16.0)


# ── SELECT ─────────────────────────────────────────


class TestSelect:
    def test_select_sets_state(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.SELECT,
            target_object_id="panel",
        )
        engine.process_intents([intent], scene)
        assert scene.get_object("panel").state == ObjectState.SELECTED

    def test_select_already_selected_no_crash(self, engine, scene):
        scene.get_object("panel").state = ObjectState.SELECTED
        intent = Intent(
            intent_type=IntentType.SELECT,
            target_object_id="panel",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1


# ── CLICK ──────────────────────────────────────────


class TestClick:
    def test_click_intent_to_select_object(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.CLICK,
            target_object_id="panel",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.SELECT_OBJECT

    def test_click_selects_panel(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.CLICK,
            target_object_id="panel",
        )
        engine.process_intents([intent], scene)
        assert scene.get_object("panel").state == ObjectState.SELECTED


# ── GRAB ───────────────────────────────────────────


class TestGrab:
    def test_grab_to_select_object(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.GRAB,
            target_object_id="card",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.SELECT_OBJECT

    def test_grab_already_grabbed_returns_none(self, engine, scene):
        scene.get_object("card").state = ObjectState.GRABBED
        intent = Intent(
            intent_type=IntentType.GRAB,
            target_object_id="card",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 0


# ── RELEASE ────────────────────────────────────────


class TestRelease:
    def test_release_to_select_object(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.RELEASE,
            target_object_id="panel",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.SELECT_OBJECT

    def test_release_missing_object_no_crash(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.RELEASE,
            target_object_id="nonexistent",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 0


# ── CANCEL ─────────────────────────────────────────


class TestCancel:
    def test_cancel_to_select_object(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.CANCEL,
            target_object_id="sphere",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1


# ── HOVER ──────────────────────────────────────────


class TestHover:
    def test_hover_when_default_selects(self, engine, scene):
        scene.get_object("panel").state = ObjectState.DEFAULT
        intent = Intent(
            intent_type=IntentType.HOVER,
            target_object_id="panel",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1

    def test_hover_when_hovered_no_action(self, engine, scene):
        scene.get_object("panel").state = ObjectState.HOVERED
        intent = Intent(
            intent_type=IntentType.HOVER,
            target_object_id="panel",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 0

    def test_hover_missing_object(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.HOVER,
            target_object_id="nonexistent",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 0


# ── NAVIGATE ───────────────────────────────────────


class TestNavigate:
    def test_navigate_action_type(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.NAVIGATE,
            target_object_id="button",
        )
        actions = engine.process_intents([intent], scene)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.NAVIGATE

    def test_navigate_no_scene_mutation(self, engine, scene):
        x_before = scene.get_object("button").x
        intent = Intent(
            intent_type=IntentType.NAVIGATE,
            target_object_id="button",
        )
        engine.process_intents([intent], scene)
        assert scene.get_object("button").x == x_before


# ── Action logging ─────────────────────────────────


class TestActionLogging:
    def test_pending_actions_cleared(self, engine, scene):
        intent = Intent(
            intent_type=IntentType.CLICK,
            target_object_id="panel",
        )
        engine.process_intents([intent], scene)
        assert len(engine.pending_actions) == 1

    def test_pending_cleared_on_new_frame(self, engine, scene):
        engine.process_intents(
            [Intent(intent_type=IntentType.CLICK, target_object_id="panel")],
            scene,
        )
        engine.process_intents([], scene)
        assert len(engine.pending_actions) == 0


# ── Multiple intents ───────────────────────────────


class TestMultipleIntents:
    def test_two_intents_two_actions(self, engine, scene):
        intents = [
            Intent(
                intent_type=IntentType.MOVE,
                target_object_id="panel",
                delta_x=1.0,
            ),
            Intent(
                intent_type=IntentType.ROTATE,
                target_object_id="card",
                rotation_delta=0.3,
            ),
        ]
        actions = engine.process_intents(intents, scene)
        assert len(actions) == 2
        assert scene.get_object("panel").x == 1.0
        assert scene.get_object("card").rotation == pytest.approx(0.3)
