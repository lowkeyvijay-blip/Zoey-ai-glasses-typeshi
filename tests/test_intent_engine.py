"""Tests for V1.9 IntentEngine.

Covers:
  - Controller event → intent translation
  - Object event → intent translation
  - Button click → CLICK + NAVIGATE
  - Panel click → CLICK + SELECT
  - GRAB / RELEASE mapping
  - CANCEL on FREEZE
  - MOVE on RESUME
  - LLM interface integration
  - Empty event list
  - Multiple events in one frame
"""

import pytest

from backend.intent.types import Intent, IntentType
from backend.intent.engine import IntentEngine
from backend.intent.llm_interface import LLMInterface, NullLLM
from backend.interaction.events import EventType, InteractionEvent
from backend.scene.object_interaction import ObjectInteractionEvent
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectType, VisualProperties


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
        visual=VisualProperties(color="#1a2a3a", label="Panel"),
        hit_radius=1.5,
    )
    s.add_object(
        obj_id="button",
        object_type=ObjectType.BUTTON,
        x=-0.5, y=0.55, z=0.0,
        visual=VisualProperties(color="#22aa66", label="OK"),
        hit_radius=0.5,
    )
    s.add_object(
        obj_id="card",
        object_type=ObjectType.CARD,
        x=0.0, y=0.7, z=-1.0,
        visual=VisualProperties(color="#2a1a3a", label="Info"),
        hit_radius=0.8,
    )
    return s


@pytest.fixture
def engine():
    return IntentEngine()


# ── Controller event mapping ───────────────────────


class TestControllerEvents:
    def test_grab_event_to_intent(self, engine):
        ev = InteractionEvent(
            event_type=EventType.GRAB,
            timestamp=1,
            hand_x=0.3, hand_y=0.4, hand_z=1.0,
            hand_label="LEFT",
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="GRABBED",
            scene=Scene(),
        )
        assert len(intents) == 1
        assert intents[0].intent_type == IntentType.GRAB
        assert intents[0].target_object_id == "sphere"
        assert intents[0].hand_label == "LEFT"

    def test_release_event_to_intent(self, engine):
        ev = InteractionEvent(
            event_type=EventType.RELEASE,
            timestamp=5,
            hand_x=0.3, hand_y=0.4,
            hand_label="RIGHT",
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="IDLE",
            scene=Scene(),
        )
        assert intents[0].intent_type == IntentType.RELEASE
        assert intents[0].target_object_id == "sphere"
        assert intents[0].hand_label == "RIGHT"

    def test_click_to_intent(self, engine):
        ev = InteractionEvent(
            event_type=EventType.CLICK,
            timestamp=10,
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="IDLE",
            scene=Scene(),
        )
        assert intents[0].intent_type == IntentType.CLICK
        assert intents[0].target_object_id == "sphere"

    def test_double_click_to_click_intent(self, engine):
        ev = InteractionEvent(
            event_type=EventType.DOUBLE_CLICK,
            timestamp=20,
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="IDLE",
            scene=Scene(),
        )
        assert intents[0].intent_type == IntentType.CLICK

    def test_freeze_to_cancel(self, engine):
        ev = InteractionEvent(
            event_type=EventType.FREEZE,
            timestamp=15,
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="GRABBED",
            scene=Scene(),
        )
        assert intents[0].intent_type == IntentType.CANCEL
        assert intents[0].target_object_id == "sphere"

    def test_resume_to_move(self, engine):
        ev = InteractionEvent(
            event_type=EventType.RESUME,
            timestamp=25,
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="GRABBED",
            scene=Scene(),
        )
        assert intents[0].intent_type == IntentType.MOVE
        assert intents[0].target_object_id == "sphere"

    def test_position_preserved(self, engine):
        ev = InteractionEvent(
            event_type=EventType.GRAB,
            timestamp=1,
            hand_x=0.7,
            hand_y=0.3,
            hand_z=2.5,
            hand_label="LEFT",
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="GRABBED",
            scene=Scene(),
        )
        assert intents[0].x == 0.7
        assert intents[0].y == 0.3
        assert intents[0].z == 2.5


# ── Object event mapping ───────────────────────────


class TestObjectEvents:
    def test_object_click(self, engine, scene):
        oe = ObjectInteractionEvent(
            event_type="CLICK",
            timestamp=10,
            hand_label="LEFT",
            object_id="panel",
            x=0.5, y=0.6, z=-0.5,
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        click_intents = [i for i in intents if i.intent_type == IntentType.CLICK]
        assert len(click_intents) == 1
        assert click_intents[0].target_object_id == "panel"

    def test_button_click_generates_navigate(self, engine, scene):
        oe = ObjectInteractionEvent(
            event_type="CLICK",
            timestamp=10,
            hand_label="RIGHT",
            object_id="button",
            x=-0.5, y=0.55, z=0.0,
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        types = [i.intent_type for i in intents]
        assert IntentType.CLICK in types
        assert IntentType.NAVIGATE in types
        nav = [i for i in intents if i.intent_type == IntentType.NAVIGATE][0]
        assert nav.target_object_id == "button"

    def test_panel_click_generates_select(self, engine, scene):
        oe = ObjectInteractionEvent(
            event_type="CLICK",
            timestamp=10,
            hand_label="LEFT",
            object_id="panel",
            x=0.5, y=0.6, z=-0.5,
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        types = [i.intent_type for i in intents]
        assert IntentType.SELECT in types

    def test_object_grab(self, engine, scene):
        oe = ObjectInteractionEvent(
            event_type="GRAB",
            timestamp=5,
            hand_label="LEFT",
            object_id="card",
            x=0.0, y=0.7, z=-1.0,
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        assert intents[0].intent_type == IntentType.GRAB
        assert intents[0].target_object_id == "card"

    def test_object_release(self, engine, scene):
        oe = ObjectInteractionEvent(
            event_type="RELEASE",
            timestamp=15,
            hand_label="RIGHT",
            object_id="panel",
            x=1.0, y=1.0, z=0.0,
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        assert intents[0].intent_type == IntentType.RELEASE
        assert intents[0].target_object_id == "panel"

    def test_card_click_no_navigate(self, engine, scene):
        """Card click produces CLICK but no NAVIGATE."""
        oe = ObjectInteractionEvent(
            event_type="CLICK",
            timestamp=10,
            hand_label="LEFT",
            object_id="card",
        )
        intents = engine.resolve(
            controller_events=[],
            obj_events=[oe],
            interaction_state="IDLE",
            scene=scene,
        )
        types = [i.intent_type for i in intents]
        assert IntentType.NAVIGATE not in types


# ── Combined events ────────────────────────────────


class TestCombined:
    def test_controller_and_object_events(self, engine, scene):
        ce = InteractionEvent(
            event_type=EventType.GRAB,
            timestamp=1,
            hand_label="LEFT",
        )
        oe = ObjectInteractionEvent(
            event_type="CLICK",
            timestamp=2,
            hand_label="LEFT",
            object_id="button",
        )
        intents = engine.resolve(
            controller_events=[ce],
            obj_events=[oe],
            interaction_state="GRABBED",
            scene=scene,
        )
        types = [i.intent_type for i in intents]
        assert IntentType.GRAB in types
        assert IntentType.CLICK in types
        assert IntentType.NAVIGATE in types

    def test_no_events_empty_intents(self, engine, scene):
        intents = engine.resolve(
            controller_events=[],
            obj_events=[],
            interaction_state="IDLE",
            scene=scene,
        )
        assert intents == []


# ── LLM integration ────────────────────────────────


class TestLLMIntegration:
    def test_null_llm_returns_no_intents(self, engine, scene):
        engine._llm = NullLLM()
        intents = engine.resolve(
            controller_events=[],
            obj_events=[],
            interaction_state="IDLE",
            scene=scene,
        )
        assert intents == []

    def test_custom_llm_adds_intents(self, scene):
        class MockLLM(LLMInterface):
            def suggest_intents(self, events, obj_events, scene, timestamp=0):
                return [
                    Intent(
                        intent_type=IntentType.NAVIGATE,
                        target_object_id="button",
                        from_llm=True,
                    )
                ]

        engine = IntentEngine(llm=MockLLM())
        intents = engine.resolve(
            controller_events=[],
            obj_events=[],
            interaction_state="IDLE",
            scene=scene,
        )
        assert len(intents) == 1
        assert intents[0].from_llm is True
        assert intents[0].intent_type == IntentType.NAVIGATE

    def test_llm_intents_merge_with_rule_intents(self, scene):
        class MockLLM(LLMInterface):
            def suggest_intents(self, events, obj_events, scene, timestamp=0):
                return [
                    Intent(
                        intent_type=IntentType.HOVER,
                        target_object_id="card",
                        from_llm=True,
                    )
                ]

        engine = IntentEngine(llm=MockLLM())
        ev = InteractionEvent(
            event_type=EventType.GRAB,
            timestamp=1,
        )
        intents = engine.resolve(
            controller_events=[ev],
            obj_events=[],
            interaction_state="GRABBED",
            scene=scene,
        )
        types = [i.intent_type for i in intents]
        assert IntentType.GRAB in types
        assert IntentType.HOVER in types
