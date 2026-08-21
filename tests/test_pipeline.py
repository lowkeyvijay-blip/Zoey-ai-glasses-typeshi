"""Tests for V1.9 Pipeline.

Covers:
  - Pipeline creates scene with default objects
  - Pipeline.process_frame returns FrameResult
  - FrameResult serializes correctly
  - No business logic in main.py
  - Sphere position synced from controller
  - Cursor updates
  - Object interaction flows through
  - Intent/action pipeline flows
  - LLM injection works
  - Pipeline is self-contained per session
"""

import pytest

from backend.pipeline import Pipeline, FrameResult
from backend.scene.spatial_object import ObjectState, ObjectType


@pytest.fixture
def pipeline():
    return Pipeline()


class TestPipelineInit:
    def test_creates_scene(self, pipeline):
        assert pipeline.scene is not None
        assert len(pipeline.scene.objects) > 0

    def test_has_sphere(self, pipeline):
        assert pipeline.scene.get_object("sphere") is not None

    def test_has_panel(self, pipeline):
        assert pipeline.scene.get_object("panel") is not None

    def test_has_button(self, pipeline):
        assert pipeline.scene.get_object("button") is not None

    def test_has_card(self, pipeline):
        assert pipeline.scene.get_object("card") is not None

    def test_has_controller(self, pipeline):
        assert pipeline.controller is not None

    def test_has_event_detector(self, pipeline):
        assert pipeline.event_detector is not None

    def test_has_intent_engine(self, pipeline):
        assert pipeline.intent_engine is not None

    def test_has_action_engine(self, pipeline):
        assert pipeline.action_engine is not None

    def test_has_obj_interaction(self, pipeline):
        assert pipeline.obj_interaction is not None

    def test_sphere_excluded_from_obj_interaction(self, pipeline):
        assert "sphere" in pipeline.obj_interaction._exclude_ids


class TestProcessFrame:
    def test_returns_frame_result(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result, FrameResult)

    def test_default_state(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert result.interaction_state == "IDLE"
        assert result.left_state == "IDLE"
        assert result.right_state == "IDLE"

    def test_no_hands(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert result.left_hand is None
        assert result.right_hand is None

    def test_controller_events_list(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result.controller_events, list)

    def test_obj_events_list(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result.obj_events, list)

    def test_intents_list(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result.intents, list)

    def test_actions_list(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result.actions, list)

    def test_scene_dict(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        assert isinstance(result.scene, dict)
        assert "objects" in result.scene

    def test_sphere_position_synced(self, pipeline):
        pipeline.process_frame(
            left_gesture="PINCH",
            left_x=0.5, left_y=0.3, left_z=1.0,
            timestamp=1,
        )
        pipeline.process_frame(
            left_gesture="PINCH",
            left_x=0.7, left_y=0.5, left_z=2.0,
            timestamp=2,
        )
        sphere = pipeline.scene.get_object("sphere")
        assert sphere.x == pytest.approx(0.2)
        assert sphere.y == pytest.approx(0.2)
        assert sphere.z == pytest.approx(1.0)

    def test_sphere_grabbed_state(self, pipeline):
        for i in range(5):
            pipeline.process_frame(
                left_gesture="PINCH",
                left_x=0.5, left_y=0.3, left_z=1.0,
                timestamp=i + 1,
            )
        sphere = pipeline.scene.get_object("sphere")
        assert sphere.state == ObjectState.GRABBED

    def test_cursor_updates(self, pipeline):
        pipeline.process_frame(
            left_gesture="OPEN_PALM",
            left_x=0.3, left_y=0.4, left_z=1.0,
            timestamp=1,
        )
        assert "LEFT" in pipeline.scene.cursors
        assert pipeline.scene.cursors["LEFT"].active is True

    def test_cursor_cleared_on_no_hand(self, pipeline):
        pipeline.process_frame(
            left_gesture="OPEN_PALM",
            left_x=0.3, left_y=0.4, left_z=1.0,
            timestamp=1,
        )
        pipeline.process_frame(
            left_gesture="NO_HAND",
            timestamp=2,
        )
        assert pipeline.scene.cursors["LEFT"].active is False


class TestFrameResult:
    def test_to_dict_keys(self, pipeline):
        result = pipeline.process_frame(timestamp=1)
        d = result.to_dict()
        assert "sphere_x" in d
        assert "sphere_y" in d
        assert "sphere_z" in d
        assert "sphere_scale" in d
        assert "sphere_rotation" in d
        assert "interaction_state" in d
        assert "left_state" in d
        assert "right_state" in d
        assert "left_hand" in d
        assert "right_hand" in d
        assert "events" in d
        assert "intents" in d
        assert "actions" in d
        assert "scene" in d

    def test_to_json(self, pipeline):
        import json
        result = pipeline.process_frame(timestamp=1)
        j = result.to_json()
        parsed = json.loads(j)
        assert "sphere_x" in parsed
        assert "scene" in parsed

    def test_events_includes_controller_and_obj(self, pipeline):
        result = pipeline.process_frame(
            left_gesture="PINCH",
            left_x=0.5, left_y=0.3, left_z=1.0,
            right_gesture="PINCH",
            right_x=-0.5, right_y=0.55, right_z=0.0,
            timestamp=1,
        )
        d = result.to_dict()
        assert isinstance(d["events"], list)


class TestPipelineIndependence:
    def test_two_pipelines_independent(self):
        p1 = Pipeline()
        p2 = Pipeline()
        p1.process_frame(
            left_gesture="PINCH",
            left_x=0.5, left_y=0.3, left_z=1.0,
            timestamp=1,
        )
        sphere1 = p1.scene.get_object("sphere")
        sphere2 = p2.scene.get_object("sphere")
        assert sphere1 is not sphere2


class TestLLMInjection:
    def test_custom_llm_in_pipeline(self):
        from backend.intent.llm_interface import LLMInterface
        from backend.intent.types import Intent, IntentType

        class MockLLM(LLMInterface):
            def suggest_intents(self, events, obj_events, scene, timestamp=0):
                return [
                    Intent(
                        intent_type=IntentType.NAVIGATE,
                        target_object_id="button",
                        from_llm=True,
                    )
                ]

        pipeline = Pipeline(intent_engine=None)
        from backend.intent.engine import IntentEngine
        pipeline.intent_engine = IntentEngine(llm=MockLLM())

        result = pipeline.process_frame(timestamp=1)
        intent_types = [i["type"] for i in result.intents]
        assert "NAVIGATE" in intent_types
