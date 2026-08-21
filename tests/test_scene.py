"""Tests for V1.8 Scene system.

Covers:
  - SpatialObject data model and serialization
  - ObjectState and ObjectType enums
  - Scene registry: add/remove/get/update
  - Hit-testing (3D Euclidean distance)
  - Hover state updates
  - SpatialCursor management
  - Scene serialization for WebSocket
  - Multiple objects coexisting
  - Visual properties
"""

import math

import pytest

from backend.scene.spatial_object import (
    ObjectState,
    ObjectType,
    SpatialCursor,
    SpatialObject,
    VisualProperties,
)
from backend.scene.scene import Scene


# ─────────────────────────────────────────────
# SpatialObject data model
# ─────────────────────────────────────────────

class TestSpatialObject:
    def test_defaults(self):
        obj = SpatialObject(id="test")
        assert obj.id == "test"
        assert obj.object_type == ObjectType.SPHERE
        assert obj.x == 0.0
        assert obj.y == 0.0
        assert obj.z == 0.0
        assert obj.rotation == 0.0
        assert obj.scale == 1.0
        assert obj.state == ObjectState.DEFAULT
        assert obj.hit_radius == 0.8

    def test_to_dict(self):
        obj = SpatialObject(
            id="s1",
            object_type=ObjectType.SPHERE,
            x=0.5, y=0.3, z=-1.0,
            visual=VisualProperties(color="#ff0000", label="Ball"),
        )
        d = obj.to_dict()
        assert d["id"] == "s1"
        assert d["type"] == "SPHERE"
        assert d["x"] == 0.5
        assert d["y"] == 0.3
        assert d["z"] == -1.0
        assert d["color"] == "#ff0000"
        assert d["label"] == "Ball"
        assert d["state"] == "DEFAULT"

    def test_to_dict_panel(self):
        obj = SpatialObject(
            id="p1",
            object_type=ObjectType.PANEL,
            visual=VisualProperties(width=2.0, height=1.0, opacity=0.8),
        )
        d = obj.to_dict()
        assert d["type"] == "PANEL"
        assert d["width"] == 2.0
        assert d["height"] == 1.0
        assert d["opacity"] == 0.8

    def test_to_dict_button(self):
        obj = SpatialObject(
            id="b1",
            object_type=ObjectType.BUTTON,
            visual=VisualProperties(label="OK"),
        )
        d = obj.to_dict()
        assert d["type"] == "BUTTON"
        assert d["label"] == "OK"

    def test_to_dict_card(self):
        obj = SpatialObject(
            id="c1",
            object_type=ObjectType.CARD,
            visual=VisualProperties(label="Info"),
        )
        d = obj.to_dict()
        assert d["type"] == "CARD"
        assert d["label"] == "Info"


class TestVisualProperties:
    def test_defaults(self):
        v = VisualProperties()
        assert v.color == "#00aaff"
        assert v.opacity == 1.0
        assert v.label == ""
        assert v.width == 1.0
        assert v.height == 1.0

    def test_custom(self):
        v = VisualProperties(color="#ff00ff", opacity=0.5, label="X", width=3.0, height=2.0)
        assert v.color == "#ff00ff"
        assert v.opacity == 0.5
        assert v.label == "X"
        assert v.width == 3.0
        assert v.height == 2.0


class TestEnums:
    def test_object_type_values(self):
        assert ObjectType.SPHERE.value == "SPHERE"
        assert ObjectType.PANEL.value == "PANEL"
        assert ObjectType.BUTTON.value == "BUTTON"
        assert ObjectType.CARD.value == "CARD"

    def test_object_state_values(self):
        assert ObjectState.DEFAULT.value == "DEFAULT"
        assert ObjectState.HOVERED.value == "HOVERED"
        assert ObjectState.SELECTED.value == "SELECTED"
        assert ObjectState.GRABBED.value == "GRABBED"


# ─────────────────────────────────────────────
# SpatialCursor
# ─────────────────────────────────────────────

class TestSpatialCursor:
    def test_defaults(self):
        c = SpatialCursor()
        assert c.x == 0.0
        assert c.y == 0.0
        assert c.z == 0.0
        assert c.active is False
        assert c.hand_label == ""

    def test_to_dict(self):
        c = SpatialCursor(x=0.5, y=0.3, z=-1.0, active=True, hand_label="LEFT")
        d = c.to_dict()
        assert d["x"] == 0.5
        assert d["y"] == 0.3
        assert d["z"] == -1.0
        assert d["active"] is True
        assert d["hand_label"] == "LEFT"


# ─────────────────────────────────────────────
# Scene registry
# ─────────────────────────────────────────────

@pytest.fixture
def scene():
    return Scene()


class TestSceneAddRemove:
    def test_add_object(self, scene):
        obj = scene.add_object(
            obj_id="test",
            object_type=ObjectType.SPHERE,
            x=0.5, y=0.3,
        )
        assert obj.id == "test"
        assert obj.object_type == ObjectType.SPHERE
        assert obj.x == 0.5

    def test_add_multiple_objects(self, scene):
        scene.add_object(obj_id="a")
        scene.add_object(obj_id="b")
        scene.add_object(obj_id="c")
        assert len(scene.objects) == 3

    def test_add_auto_generates_id(self, scene):
        obj = scene.add_object()
        assert obj.id.startswith("sphere_")

    def test_add_panel_auto_id(self, scene):
        obj = scene.add_object(object_type=ObjectType.PANEL)
        assert obj.id.startswith("panel_")

    def test_remove_object(self, scene):
        scene.add_object(obj_id="x")
        assert scene.remove_object("x") is True
        assert scene.get_object("x") is None

    def test_remove_nonexistent(self, scene):
        assert scene.remove_object("nope") is False

    def test_get_object(self, scene):
        scene.add_object(obj_id="found")
        assert scene.get_object("found") is not None
        assert scene.get_object("found").id == "found"

    def test_get_nonexistent(self, scene):
        assert scene.get_object("nope") is None


class TestSceneUpdate:
    def test_update_position(self, scene):
        scene.add_object(obj_id="o")
        result = scene.update_object("o", x=1.0, y=2.0, z=3.0)
        assert result is True
        obj = scene.get_object("o")
        assert obj.x == 1.0
        assert obj.y == 2.0
        assert obj.z == 3.0

    def test_update_rotation_scale(self, scene):
        scene.add_object(obj_id="o")
        scene.update_object("o", rotation=0.5, scale=2.0)
        obj = scene.get_object("o")
        assert obj.rotation == 0.5
        assert obj.scale == 2.0

    def test_update_state(self, scene):
        scene.add_object(obj_id="o")
        scene.update_object("o", state=ObjectState.HOVERED)
        assert scene.get_object("o").state == ObjectState.HOVERED

    def test_update_visual(self, scene):
        scene.add_object(obj_id="o")
        v = VisualProperties(color="#ff0000", label="Red")
        scene.update_object("o", visual=v)
        obj = scene.get_object("o")
        assert obj.visual.color == "#ff0000"
        assert obj.visual.label == "Red"

    def test_update_nonexistent(self, scene):
        assert scene.update_object("nope", x=1.0) is False

    def test_partial_update(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0)
        scene.update_object("o", x=5.0)
        obj = scene.get_object("o")
        assert obj.x == 5.0
        assert obj.y == 0.0


# ─────────────────────────────────────────────
# Hit-testing
# ─────────────────────────────────────────────

class TestHitTesting:
    def test_hit_exact_center(self, scene):
        scene.add_object(obj_id="o", x=1.0, y=1.0, z=0.0, hit_radius=0.5)
        result = scene.hit_test(1.0, 1.0, 0.0)
        assert result is not None
        assert result.id == "o"

    def test_miss_too_far(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0, z=0.0, hit_radius=0.5)
        result = scene.hit_test(2.0, 2.0, 0.0)
        assert result is None

    def test_hit_within_radius(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0, z=0.0, hit_radius=1.0)
        result = scene.hit_test(0.5, 0.5, 0.0)
        assert result is not None

    def test_miss_at_boundary(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0, z=0.0, hit_radius=0.5)
        result = scene.hit_test(0.6, 0.0, 0.0)
        assert result is None

    def test_closest_object_wins(self, scene):
        scene.add_object(obj_id="far", x=2.0, y=0.0, z=0.0, hit_radius=1.5)
        scene.add_object(obj_id="near", x=0.3, y=0.0, z=0.0, hit_radius=0.5)
        result = scene.hit_test(0.0, 0.0, 0.0)
        assert result is not None
        assert result.id == "near"

    def test_hit_3d_distance(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0, z=2.0, hit_radius=2.5)
        result = scene.hit_test(0.0, 0.0, 0.0)
        assert result is not None

    def test_miss_3d_distance(self, scene):
        scene.add_object(obj_id="o", x=0.0, y=0.0, z=5.0, hit_radius=0.5)
        result = scene.hit_test(0.0, 0.0, 0.0)
        assert result is None

    def test_no_objects(self, scene):
        result = scene.hit_test(0.0, 0.0, 0.0)
        assert result is None

    def test_hit_radius_scaled(self, scene):
        scene.add_object(obj_id="o", x=1.0, y=0.0, z=0.0, scale=2.0, hit_radius=0.5)
        # effective_radius = 0.5 * 2.0 = 1.0
        result = scene.hit_test(0.5, 0.0, 0.0)
        assert result is not None

    def test_miss_radius_scaled(self, scene):
        scene.add_object(obj_id="o", x=1.0, y=0.0, z=0.0, scale=0.5, hit_radius=0.5)
        # effective_radius = 0.5 * 0.5 = 0.25
        result = scene.hit_test(0.5, 0.0, 0.0)
        assert result is None


# ─────────────────────────────────────────────
# Hover state management
# ─────────────────────────────────────────────

class TestHoverStates:
    def test_hover_closest_object(self, scene):
        scene.add_object(obj_id="a", x=0.0, y=0.0, z=0.0, hit_radius=1.0)
        scene.add_object(obj_id="b", x=2.0, y=0.0, z=0.0, hit_radius=1.0)
        hovered_id = scene.update_hover_states(0.0, 0.0, 0.0)
        assert hovered_id == "a"
        assert scene.get_object("a").state == ObjectState.HOVERED
        assert scene.get_object("b").state == ObjectState.DEFAULT

    def test_hover_clears_on_move_away(self, scene):
        scene.add_object(obj_id="a", x=0.0, y=0.0, z=0.0, hit_radius=0.5)
        scene.update_hover_states(0.0, 0.0, 0.0)
        assert scene.get_object("a").state == ObjectState.HOVERED
        scene.update_hover_states(2.0, 2.0, 0.0)
        assert scene.get_object("a").state == ObjectState.DEFAULT

    def test_grabbed_object_not_hovered(self, scene):
        scene.add_object(obj_id="a", x=0.0, y=0.0, z=0.0, hit_radius=1.0)
        scene.update_object("a", state=ObjectState.GRABBED)
        scene.update_hover_states(0.0, 0.0, 0.0)
        assert scene.get_object("a").state == ObjectState.GRABBED

    def test_selected_object_not_hovered(self, scene):
        scene.add_object(obj_id="a", x=0.0, y=0.0, z=0.0, hit_radius=1.0)
        scene.update_object("a", state=ObjectState.SELECTED)
        scene.update_hover_states(0.0, 0.0, 0.0)
        assert scene.get_object("a").state == ObjectState.SELECTED

    def test_hover_returns_none_when_empty(self, scene):
        result = scene.update_hover_states(0.0, 0.0, 0.0)
        assert result is None


# ─────────────────────────────────────────────
# Cursor management
# ─────────────────────────────────────────────

class TestCursorManagement:
    def test_update_cursor(self, scene):
        scene.update_cursor("LEFT", 0.5, 0.3, -1.0)
        assert "LEFT" in scene.cursors
        c = scene.cursors["LEFT"]
        assert c.x == 0.5
        assert c.active is True
        assert c.hand_label == "LEFT"

    def test_clear_cursor(self, scene):
        scene.update_cursor("RIGHT", 0.5, 0.3, 0.0)
        scene.clear_cursor("RIGHT")
        assert scene.cursors["RIGHT"].active is False

    def test_clear_nonexistent_cursor(self, scene):
        scene.clear_cursor("NOPE")
        assert "NOPE" not in scene.cursors

    def test_multiple_cursors(self, scene):
        scene.update_cursor("LEFT", 0.1, 0.2, 0.0)
        scene.update_cursor("RIGHT", 0.8, 0.9, 0.0)
        assert len(scene.cursors) == 2


# ─────────────────────────────────────────────
# Scene serialization
# ─────────────────────────────────────────────

class TestSceneSerialization:
    def test_serialize_empty(self, scene):
        data = scene.serialize()
        assert data["objects"] == []
        assert data["cursors"] == {}

    def test_serialize_objects(self, scene):
        scene.add_object(obj_id="a", object_type=ObjectType.SPHERE, x=0.5)
        scene.add_object(obj_id="b", object_type=ObjectType.PANEL, x=1.0)
        data = scene.serialize()
        assert len(data["objects"]) == 2
        ids = {o["id"] for o in data["objects"]}
        assert "a" in ids
        assert "b" in ids

    def test_serialize_cursors(self, scene):
        scene.update_cursor("LEFT", 0.1, 0.2, 0.0)
        data = scene.serialize()
        assert "LEFT" in data["cursors"]
        assert data["cursors"]["LEFT"]["x"] == 0.1

    def test_serialize_preserves_state(self, scene):
        scene.add_object(obj_id="o")
        scene.update_object("o", state=ObjectState.HOVERED)
        data = scene.serialize()
        obj_data = [o for o in data["objects"] if o["id"] == "o"][0]
        assert obj_data["state"] == "HOVERED"

    def test_serialize_preserves_visuals(self, scene):
        scene.add_object(
            obj_id="o",
            visual=VisualProperties(color="#ff0000", label="Red Ball"),
        )
        data = scene.serialize()
        obj_data = [o for o in data["objects"] if o["id"] == "o"][0]
        assert obj_data["color"] == "#ff0000"
        assert obj_data["label"] == "Red Ball"


# ─────────────────────────────────────────────
# Multiple objects coexistence
# ─────────────────────────────────────────────

class TestMultipleObjects:
    def test_five_objects(self, scene):
        for i in range(5):
            scene.add_object(
                obj_id=f"obj_{i}",
                object_type=ObjectType.SPHERE,
                x=float(i),
            )
        assert len(scene.objects) == 5

    def test_mixed_types(self, scene):
        scene.add_object(obj_id="s", object_type=ObjectType.SPHERE)
        scene.add_object(obj_id="p", object_type=ObjectType.PANEL)
        scene.add_object(obj_id="b", object_type=ObjectType.BUTTON)
        scene.add_object(obj_id="c", object_type=ObjectType.CARD)
        assert len(scene.objects) == 4

    def test_remove_one_of_many(self, scene):
        scene.add_object(obj_id="a")
        scene.add_object(obj_id="b")
        scene.add_object(obj_id="c")
        scene.remove_object("b")
        assert len(scene.objects) == 2
        assert scene.get_object("a") is not None
        assert scene.get_object("b") is None
        assert scene.get_object("c") is not None

    def test_each_object_independent_state(self, scene):
        scene.add_object(obj_id="a")
        scene.add_object(obj_id="b")
        scene.update_object("a", state=ObjectState.HOVERED)
        assert scene.get_object("a").state == ObjectState.HOVERED
        assert scene.get_object("b").state == ObjectState.DEFAULT

    def test_hit_test_multiple(self, scene):
        scene.add_object(obj_id="a", x=0.0, y=0.0, z=0.0, hit_radius=0.5)
        scene.add_object(obj_id="b", x=1.0, y=0.0, z=0.0, hit_radius=0.5)
        scene.add_object(obj_id="c", x=2.0, y=0.0, z=0.0, hit_radius=0.5)
        assert scene.hit_test(0.0, 0.0, 0.0).id == "a"
        assert scene.hit_test(1.0, 0.0, 0.0).id == "b"
        assert scene.hit_test(2.0, 0.0, 0.0).id == "c"
