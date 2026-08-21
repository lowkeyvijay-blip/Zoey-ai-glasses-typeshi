"""Tests for V1.8 ObjectInteractionManager.

Covers:
  1. Hovering each object type
  2. Pinch-to-select (short pinch)
  3. Pinch-to-grab (sustained pinch)
  4. Grab offset / no jumping
  5. Moving a grabbed non-primary object
  6. Release (OPEN_PALM)
  7. NO_HAND safe release
  8. Click on button
  9. Click on panel/card
  10. Multiple objects independently
  11. Object grab conflict between two hands
  12. Primary sphere behavior unchanged (excluded)
"""

import pytest

from backend.scene.spatial_object import (
    ObjectState,
    ObjectType,
    SpatialObject,
    VisualProperties,
)
from backend.scene.scene import Scene
from backend.scene.object_interaction import (
    CLICK_GRAB_THRESHOLD,
    ObjectInteractionEvent,
    ObjectInteractionManager,
)


# ── Fixtures ───────────────────────────────────────

def _make_scene() -> Scene:
    scene = Scene()
    scene.add_object(
        obj_id="sphere",
        object_type=ObjectType.SPHERE,
        x=0.0, y=0.0, z=0.0,
        hit_radius=0.8,
    )
    scene.add_object(
        obj_id="panel",
        object_type=ObjectType.PANEL,
        x=0.5, y=0.6, z=-0.5,
        scale=1.0,
        hit_radius=1.5,
    )
    scene.add_object(
        obj_id="button",
        object_type=ObjectType.BUTTON,
        x=-0.5, y=0.55, z=0.0,
        hit_radius=0.5,
    )
    scene.add_object(
        obj_id="card",
        object_type=ObjectType.CARD,
        x=0.0, y=0.7, z=-1.0,
        hit_radius=0.8,
    )
    return scene


@pytest.fixture
def scene():
    return _make_scene()


@pytest.fixture
def mgr():
    return ObjectInteractionManager(exclude_ids={"sphere"})


# ── 1. Hovering each object ────────────────────────

class TestHover:
    def test_hover_panel(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=1,
        )
        assert scene.get_object("panel").state == ObjectState.HOVERED

    def test_hover_button(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            right_gesture="OPEN_PALM",
            right_x=-0.5, right_y=0.55, right_z=0.0,
            timestamp=1,
        )
        assert scene.get_object("button").state == ObjectState.HOVERED

    def test_hover_card(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.0, left_y=0.7, left_z=-1.0,
            timestamp=1,
        )
        assert scene.get_object("card").state == ObjectState.HOVERED

    def test_sphere_excluded(self, scene, mgr):
        """Sphere is excluded — hovering near it should not change its state."""
        sphere = scene.get_object("sphere")
        sphere.state = ObjectState.DEFAULT
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.0, left_y=0.0, left_z=0.0,
            timestamp=1,
        )
        assert sphere.state == ObjectState.DEFAULT

    def test_move_away_clears_hover(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=1,
        )
        assert scene.get_object("panel").state == ObjectState.HOVERED
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=5.0, left_y=5.0, left_z=5.0,
            timestamp=2,
        )
        assert scene.get_object("panel").state == ObjectState.DEFAULT

    def test_no_hand_clears_hover(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=1,
        )
        assert scene.get_object("panel").state == ObjectState.HOVERED
        mgr.process_frame(
            scene=scene,
            left_gesture="NO_HAND",
            timestamp=2,
        )
        assert scene.get_object("panel").state == ObjectState.DEFAULT


# ── 2. Pinch-to-select (short pinch) ──────────────

class TestSelect:
    def test_short_pinch_selects(self, scene, mgr):
        """Pinch for <= CLICK_GRAB_THRESHOLD frames → SELECTED."""
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        assert scene.get_object("panel").state == ObjectState.SELECTED

    def test_pinch_release_after_select_emits_click(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=CLICK_GRAB_THRESHOLD + 1,
        )
        click_events = [e for e in events if e.event_type == "CLICK"]
        assert len(click_events) == 1
        assert click_events[0].object_id == "panel"
        # Cursor is still near panel, so it re-hovers — that is correct
        assert scene.get_object("panel").state in (
            ObjectState.DEFAULT,
            ObjectState.HOVERED,
        )

    def test_select_button(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                right_gesture="PINCH",
                right_x=-0.5, right_y=0.55, right_z=0.0,
                timestamp=i + 1,
            )
        assert scene.get_object("button").state == ObjectState.SELECTED

    def test_select_card(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.0, left_y=0.7, left_z=-1.0,
                timestamp=i + 1,
            )
        assert scene.get_object("card").state == ObjectState.SELECTED


# ── 3. Pinch-to-grab (sustained pinch) ─────────────

class TestGrab:
    def test_sustained_pinch_grabs(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        assert scene.get_object("panel").state == ObjectState.GRABBED
        assert scene.get_object("panel").grabbed_by == "LEFT"

    def test_grab_emits_event(self, scene, mgr):
        all_events = []
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            evts = mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
            all_events.extend(evts)
        grabs = [e for e in all_events if e.event_type == "GRAB"]
        assert len(grabs) == 1
        assert grabs[0].object_id == "panel"

    def test_grab_button(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                right_gesture="PINCH",
                right_x=-0.5, right_y=0.55, right_z=0.0,
                timestamp=i + 1,
            )
        assert scene.get_object("button").state == ObjectState.GRABBED
        assert scene.get_object("button").grabbed_by == "RIGHT"

    def test_grab_card(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.0, left_y=0.7, left_z=-1.0,
                timestamp=i + 1,
            )
        assert scene.get_object("card").state == ObjectState.GRABBED
        assert scene.get_object("card").grabbed_by == "LEFT"


# ── 4. Grab offset / no jumping ────────────────────

class TestGrabOffset:
    def test_grab_offset_prevents_jump(self, scene, mgr):
        """Object should not teleport to cursor on grab start."""
        panel = scene.get_object("panel")
        cursor_x = 0.55
        cursor_y = 0.65
        cursor_z = -0.4

        # Reach threshold + 1 frame
        for i in range(CLICK_GRAB_THRESHOLD + 1):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=cursor_x, left_y=cursor_y, left_z=cursor_z,
                timestamp=i + 1,
            )

        # Object position should be unchanged (not teleported)
        assert panel.x == 0.5
        assert panel.y == 0.6
        assert panel.z == -0.5

    def test_offset_stored_correctly(self, scene, mgr):
        cursor_x = 0.55
        cursor_y = 0.65
        cursor_z = -0.4

        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=cursor_x, left_y=cursor_y, left_z=cursor_z,
                timestamp=i + 1,
            )

        hs = mgr.get_hand_state("LEFT")
        assert hs is not None
        assert hs.grab_offset_x == pytest.approx(cursor_x - 0.5)
        assert hs.grab_offset_y == pytest.approx(cursor_y - 0.6)
        assert hs.grab_offset_z == pytest.approx(cursor_z - (-0.5))


# ── 5. Moving a grabbed object ─────────────────────

class TestMoveGrabbed:
    def test_move_panel(self, scene, mgr):
        panel = scene.get_object("panel")
        # Grab
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )

        # Move hand
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=1.0, left_y=1.0, left_z=0.0,
            timestamp=20,
        )

        assert panel.x == pytest.approx(1.0)
        assert panel.y == pytest.approx(1.0)
        assert panel.z == pytest.approx(0.0)
        assert panel.state == ObjectState.GRABBED

    def test_move_card(self, scene, mgr):
        card = scene.get_object("card")
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                right_gesture="PINCH",
                right_x=0.0, right_y=0.7, right_z=-1.0,
                timestamp=i + 1,
            )

        mgr.process_frame(
            scene=scene,
            right_gesture="PINCH",
            right_x=2.0, right_y=0.3, right_z=-0.5,
            timestamp=20,
        )

        assert card.x == pytest.approx(2.0)
        assert card.y == pytest.approx(0.3)
        assert card.z == pytest.approx(-0.5)


# ── 6. Release (OPEN_PALM) ─────────────────────────

class TestRelease:
    def test_release_panel(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        assert scene.get_object("panel").state == ObjectState.GRABBED

        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=20,
        )
        assert scene.get_object("panel").state == ObjectState.DEFAULT
        assert scene.get_object("panel").grabbed_by is None
        releases = [e for e in events if e.event_type == "RELEASE"]
        assert len(releases) == 1
        assert releases[0].object_id == "panel"

    def test_release_resets_hand_state(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=-0.5, left_y=0.55, left_z=0.0,
                timestamp=i + 1,
            )
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=20,
        )
        hs = mgr.get_hand_state("LEFT")
        assert hs is not None
        assert hs.state == "IDLE"
        assert hs.target_object_id is None

    def test_release_panel_stays_at_last_position(self, scene, mgr):
        panel = scene.get_object("panel")
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=2.0, left_y=2.0, left_z=1.0,
            timestamp=15,
        )
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=2.0, left_y=2.0, left_z=1.0,
            timestamp=16,
        )
        assert panel.x == pytest.approx(2.0)
        assert panel.y == pytest.approx(2.0)
        assert panel.z == pytest.approx(1.0)


# ── 7. NO_HAND safe release ────────────────────────

class TestNoHandRelease:
    def test_no_hand_releases_grabbed_object(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )

        events = mgr.process_frame(
            scene=scene,
            left_gesture="NO_HAND",
            timestamp=20,
        )
        assert scene.get_object("panel").state == ObjectState.DEFAULT
        assert scene.get_object("panel").grabbed_by is None
        releases = [e for e in events if e.event_type == "RELEASE"]
        assert len(releases) == 1
        assert releases[0].object_id == "panel"

    def test_no_hand_clears_hover(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=1,
        )
        assert scene.get_object("button").state == ObjectState.HOVERED
        mgr.process_frame(
            scene=scene,
            left_gesture="NO_HAND",
            timestamp=2,
        )
        hs = mgr.get_hand_state("LEFT")
        assert hs.state == "IDLE"
        assert scene.get_object("button").state == ObjectState.DEFAULT


# ── 8. Click on button ─────────────────────────────

class TestClickButton:
    def test_click_button_emits_click(self, scene, mgr):
        # Hover first
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=1,
        )
        assert scene.get_object("button").state == ObjectState.HOVERED

        # Short pinch
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=2,
        )
        assert scene.get_object("button").state == ObjectState.SELECTED

        # Release quickly
        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=3,
        )
        clicks = [e for e in events if e.event_type == "CLICK"]
        assert len(clicks) == 1
        assert clicks[0].object_id == "button"
        # Cursor still near button → re-hover is fine
        assert scene.get_object("button").state in (
            ObjectState.DEFAULT,
            ObjectState.HOVERED,
        )

    def test_click_button_without_prior_hover(self, scene, mgr):
        """Pinch directly on button from IDLE → SELECTED → release → CLICK."""
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=1,
        )
        assert scene.get_object("button").state == ObjectState.SELECTED

        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=2,
        )
        clicks = [e for e in events if e.event_type == "CLICK"]
        assert len(clicks) == 1
        assert clicks[0].object_id == "button"


# ── 9. Click on panel/card ─────────────────────────

class TestClickPanelCard:
    def test_click_panel(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                timestamp=i + 1,
            )
        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=CLICK_GRAB_THRESHOLD + 1,
        )
        clicks = [e for e in events if e.event_type == "CLICK"]
        assert len(clicks) == 1
        assert clicks[0].object_id == "panel"

    def test_click_card(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD):
            mgr.process_frame(
                scene=scene,
                right_gesture="PINCH",
                right_x=0.0, right_y=0.7, right_z=-1.0,
                timestamp=i + 1,
            )
        events = mgr.process_frame(
            scene=scene,
            right_gesture="OPEN_PALM",
            right_x=0.0, right_y=0.7, right_z=-1.0,
            timestamp=CLICK_GRAB_THRESHOLD + 1,
        )
        clicks = [e for e in events if e.event_type == "CLICK"]
        assert len(clicks) == 1
        assert clicks[0].object_id == "card"


# ── 10. Multiple objects independently ──────────────

class TestMultipleObjects:
    def test_independent_states(self, scene, mgr):
        """Each object tracks its own state independently."""
        # Hover panel with left hand
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            timestamp=1,
        )
        assert scene.get_object("panel").state == ObjectState.HOVERED
        assert scene.get_object("button").state == ObjectState.DEFAULT
        assert scene.get_object("card").state == ObjectState.DEFAULT

        # Both hands active — left still hovers panel, right hovers button
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            right_gesture="OPEN_PALM",
            right_x=-0.5, right_y=0.55, right_z=0.0,
            timestamp=2,
        )
        assert scene.get_object("panel").state == ObjectState.HOVERED
        assert scene.get_object("button").state == ObjectState.HOVERED
        assert scene.get_object("card").state == ObjectState.DEFAULT

    def test_two_hands_different_objects(self, scene, mgr):
        """Each hand can interact with a different object."""
        # Left grabs panel
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                right_gesture="PINCH",
                right_x=-0.5, right_y=0.55, right_z=0.0,
                timestamp=i + 1,
            )

        assert scene.get_object("panel").state == ObjectState.GRABBED
        assert scene.get_object("panel").grabbed_by == "LEFT"
        assert scene.get_object("button").state == ObjectState.GRABBED
        assert scene.get_object("button").grabbed_by == "RIGHT"

    def test_release_one_not_other(self, scene, mgr):
        """Releasing one hand doesn't affect the other's grab."""
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                right_gesture="PINCH",
                right_x=-0.5, right_y=0.55, right_z=0.0,
                timestamp=i + 1,
            )

        # Release left
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            right_gesture="PINCH",
            right_x=-0.5, right_y=0.55, right_z=0.0,
            timestamp=20,
        )

        assert scene.get_object("panel").state == ObjectState.DEFAULT
        assert scene.get_object("button").state == ObjectState.GRABBED
        assert scene.get_object("button").grabbed_by == "RIGHT"


# ── 11. Two-hand grab conflict ─────────────────────

class TestGrabConflict:
    def test_second_hand_cannot_grab_occupied_object(self, scene, mgr):
        """An object grabbed by hand A cannot be grabbed by hand B."""
        # Left grabs panel
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                right_gesture="OPEN_PALM",
                right_x=0.5, right_y=0.6, right_z=-0.5,
                timestamp=i + 1,
            )

        assert scene.get_object("panel").grabbed_by == "LEFT"

        # Right hand pinches on same object
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            right_gesture="PINCH",
            right_x=0.5, right_y=0.6, right_z=-0.5,
            timestamp=20,
        )

        # Right hand should not have grabbed it
        right_hs = mgr.get_hand_state("RIGHT")
        assert right_hs.target_object_id != "panel" or right_hs.state != "GRABBED"
        # Left still owns it
        assert scene.get_object("panel").grabbed_by == "LEFT"

    def test_grabbed_object_stays_with_owner_during_conflict(self, scene, mgr):
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                right_gesture="PINCH",
                right_x=0.5, right_y=0.6, right_z=-0.5,
                timestamp=i + 1,
            )

        panel = scene.get_object("panel")
        left_owns = panel.grabbed_by == "LEFT"
        right_owns = panel.grabbed_by == "RIGHT"
        assert left_owns or right_owns
        # Only one hand can own it
        assert not (left_owns and right_owns)


# ── 12. Primary sphere unchanged ───────────────────

class TestPrimarySphereUnchanged:
    def test_sphere_never_hovered(self, scene, mgr):
        """ObjectInteractionManager should never hover the sphere."""
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.0, left_y=0.0, left_z=0.0,
            timestamp=1,
        )
        sphere = scene.get_object("sphere")
        assert sphere.state == ObjectState.DEFAULT

    def test_sphere_never_grabbed(self, scene, mgr):
        """ObjectInteractionManager should never grab the sphere."""
        for i in range(10):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.0, left_y=0.0, left_z=0.0,
                timestamp=i + 1,
            )
        sphere = scene.get_object("sphere")
        assert sphere.state == ObjectState.DEFAULT
        assert sphere.grabbed_by is None

    def test_sphere_excluded_from_hit_test(self, scene, mgr):
        """Hit-testing should skip the sphere even if cursor is at its position."""
        result = mgr._find_hovered_object(scene, 0.0, 0.0, 0.0)
        # Sphere at (0,0,0) excluded; panel at (0.5,0.6,-0.5) is within its
        # hit_radius=1.5 from (0,0,0), so it IS found.  Move far away to
        # confirm sphere is excluded and nothing else is found.
        result_far = mgr._find_hovered_object(scene, 50.0, 50.0, 50.0)
        assert result_far is None
        # Verify sphere is never returned
        assert result != "sphere"

    def test_sphere_state_untouched_by_manager(self, scene, mgr):
        """If caller sets sphere state externally, manager doesn't touch it."""
        sphere = scene.get_object("sphere")
        sphere.state = ObjectState.GRABBED
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=0.0, left_y=0.0, left_z=0.0,
            timestamp=1,
        )
        assert sphere.state == ObjectState.GRABBED


# ── Edge cases ─────────────────────────────────────

class TestEdgeCases:
    def test_all_hands_lost(self, scene, mgr):
        """Both hands disappear — all objects should be DEFAULT."""
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=0.5, left_y=0.6, left_z=-0.5,
            right_gesture="PINCH",
            right_x=-0.5, right_y=0.55, right_z=0.0,
            timestamp=1,
        )
        for i in range(CLICK_GRAB_THRESHOLD + 2):
            mgr.process_frame(
                scene=scene,
                left_gesture="PINCH",
                left_x=0.5, left_y=0.6, left_z=-0.5,
                right_gesture="PINCH",
                right_x=-0.5, right_y=0.55, right_z=0.0,
                timestamp=i + 2,
            )

        mgr.process_frame(
            scene=scene,
            left_gesture="NO_HAND",
            right_gesture="NO_HAND",
            timestamp=20,
        )

        assert scene.get_object("panel").state == ObjectState.DEFAULT
        assert scene.get_object("button").state == ObjectState.DEFAULT

    def test_process_frame_returns_events(self, scene, mgr):
        """process_frame returns a list (possibly empty)."""
        result = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=5.0, left_y=5.0, left_z=5.0,
            timestamp=1,
        )
        assert isinstance(result, list)

    def test_event_log_cleared_each_frame(self, scene, mgr):
        mgr.process_frame(
            scene=scene,
            left_gesture="PINCH",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=1,
        )
        # Only one frame's events should be in the return value
        events = mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=2,
        )
        # Should have at most one event (the click)
        assert len(events) <= 1

    def test_closest_object_wins(self, scene, mgr):
        """When cursor is near multiple objects, closest one is hovered."""
        # Panel at (0.5, 0.6, -0.5), button at (-0.5, 0.55, 0.0)
        # Place cursor near button
        mgr.process_frame(
            scene=scene,
            left_gesture="OPEN_PALM",
            left_x=-0.5, left_y=0.55, left_z=0.0,
            timestamp=1,
        )
        assert scene.get_object("button").state == ObjectState.HOVERED
        assert scene.get_object("panel").state == ObjectState.DEFAULT
