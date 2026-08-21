"""Tests for V2.0 Assistant interface and rule engine."""

import pytest
from backend.assistant.interface import (
    AssistantCommand,
    AssistantInterface,
    AssistantResponse,
)
from backend.assistant.rule_engine import RuleBasedAssistant
from backend.scene.scene import Scene
from backend.scene.spatial_object import ObjectType, VisualProperties


@pytest.fixture
def scene():
    s = Scene()
    s.add_object(
        obj_id="panel",
        object_type=ObjectType.PANEL,
        x=0.5, y=0.6, z=-0.5,
        visual=VisualProperties(color="#1a2a3a"),
        hit_radius=1.5,
    )
    s.add_object(
        obj_id="button",
        object_type=ObjectType.BUTTON,
        x=-0.5, y=0.55, z=0.0,
        visual=VisualProperties(color="#22aa66"),
        hit_radius=0.5,
    )
    s.add_object(
        obj_id="card",
        object_type=ObjectType.CARD,
        x=0.0, y=0.7, z=-1.0,
        visual=VisualProperties(color="#2a1a3a"),
        hit_radius=0.8,
    )
    return s


class TestAssistantInterface:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            AssistantInterface()

    def test_rule_based_is_concrete(self):
        assistant = RuleBasedAssistant()
        assert isinstance(assistant, AssistantInterface)


class TestRuleBasedAssistant:
    def test_idle_returns_no_commands(self):
        assistant = RuleBasedAssistant()
        response = assistant.interpret(interaction_state="IDLE")
        assert len(response.commands) == 0

    def test_grab_state_returns_grab(self):
        assistant = RuleBasedAssistant()
        response = assistant.interpret(
            interaction_state="GRABBED",
            selected_object_id="panel",
        )
        assert AssistantCommand.GRAB in response.commands

    def test_hover_panel_returns_select(self):
        assistant = RuleBasedAssistant(scene=Scene())
        response = assistant.interpret(
            interaction_state="IDLE",
            hovered_object_id="panel",
            gesture="OPEN_PALM",
        )
        assert AssistantCommand.SELECT in response.commands

    def test_pinch_on_button_returns_click_navigate(self):
        s = Scene()
        s.add_object(
            obj_id="button",
            object_type=ObjectType.BUTTON,
            hit_radius=0.5,
        )
        assistant = RuleBasedAssistant(scene=s)
        response = assistant.interpret(
            interaction_state="IDLE",
            hovered_object_id="button",
            gesture="PINCH",
        )
        assert AssistantCommand.CLICK in response.commands
        assert AssistantCommand.NAVIGATE in response.commands

    def test_pinch_on_panel_returns_click_select(self):
        s = Scene()
        s.add_object(
            obj_id="panel",
            object_type=ObjectType.PANEL,
            hit_radius=1.5,
        )
        assistant = RuleBasedAssistant(scene=s)
        response = assistant.interpret(
            interaction_state="IDLE",
            hovered_object_id="panel",
            gesture="PINCH",
        )
        assert AssistantCommand.CLICK in response.commands
        assert AssistantCommand.SELECT in response.commands

    def test_pinch_on_card_returns_grab(self):
        s = Scene()
        s.add_object(
            obj_id="card",
            object_type=ObjectType.CARD,
            hit_radius=0.8,
        )
        assistant = RuleBasedAssistant(scene=s)
        response = assistant.interpret(
            interaction_state="IDLE",
            hovered_object_id="card",
            gesture="PINCH",
        )
        assert AssistantCommand.GRAB in response.commands

    def test_release_grabbed(self):
        assistant = RuleBasedAssistant()
        response = assistant.interpret(
            interaction_state="GRABBED",
            gesture="OPEN_PALM",
            selected_object_id="sphere",
        )
        assert AssistantCommand.RELEASE in response.commands

    def test_target_object_propagated(self):
        assistant = RuleBasedAssistant()
        response = assistant.interpret(
            interaction_state="GRABBED",
            selected_object_id="card",
        )
        assert response.target_object_id == "card"

    def test_message_not_empty(self):
        assistant = RuleBasedAssistant()
        response = assistant.interpret(interaction_state="IDLE")
        assert isinstance(response.message, str)

    def test_set_scene(self):
        assistant = RuleBasedAssistant()
        s = Scene()
        assistant.set_scene(s)
        assert assistant._scene is s
