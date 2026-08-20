"""Tests for V1.4 Spatial Interaction Controller.

Covers:
  - Initial IDLE state
  - PINCH → GRABBED transition
  - Grab offset (no jump on grab)
  - Movement while GRABBED
  - OPEN_PALM → IDLE release
  - Release position persistence
  - Non-grab gestures from IDLE (stay IDLE)
  - Freeze while GRABBED (POINT/FIST/RELAXED/UNKNOWN)
  - PINCH resume after freeze
  - NO_HAND release
  - Edge cases
"""

import pytest

from backend.interaction.controller import (
    InteractionState,
    SpatialInteractionController,
)


# ─────────────────────────────────────────────
# IDLE state
# ─────────────────────────────────────────────

def test_initial_state_is_idle(controller):
    result = controller.process_frame("UNKNOWN")
    assert result.state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_initial_sphere_at_origin(controller):
    result = controller.process_frame("UNKNOWN")
    assert result.sphere_position.x == 0.0
    assert result.sphere_position.y == 0.0


# ─────────────────────────────────────────────
# PINCH → GRABBED
# ─────────────────────────────────────────────

def test_pinch_grabs_from_idle(controller):
    result = controller.process_frame(
        "PINCH", hand_x=0.3, hand_y=0.4
    )
    assert result.state == InteractionState.GRABBED
    assert result.interaction_state == "GRABBED"


def test_sphere_stays_at_previous_position_on_grab(controller):
    """Sphere should NOT jump to hand position on grab.
    It stays where it was; offset prevents the jump."""
    result = controller.process_frame(
        "PINCH", hand_x=0.3, hand_y=0.4
    )
    assert result.sphere_position.x == 0.0
    assert result.sphere_position.y == 0.0


# ─────────────────────────────────────────────
# Grab offset prevents jumping
# ─────────────────────────────────────────────

def test_no_jump_on_grab_from_nonzero_position(controller):
    controller._sphere.x = 1.0
    controller._sphere.y = 2.0

    result = controller.process_frame(
        "PINCH", hand_x=0.3, hand_y=0.4
    )

    # Sphere should stay at its old position, not jump to hand
    assert result.sphere_position.x == 1.0
    assert result.sphere_position.y == 2.0


def test_offset_captured_correctly(controller):
    controller._sphere.x = 0.5
    controller._sphere.y = 0.3

    controller.process_frame("PINCH", hand_x=0.2, hand_y=0.1)

    # offset = sphere - hand at grab time
    assert controller._offset.dx == pytest.approx(0.3)
    assert controller._offset.dy == pytest.approx(0.2)


# ─────────────────────────────────────────────
# Movement while GRABBED
# ─────────────────────────────────────────────

def test_sphere_follows_hand_while_grabbed(controller):
    """After grab, sphere = hand + offset.
    Sphere starts at (0,0), grab at (0.5, 0.5), offset = (-0.5, -0.5).
    Next PINCH at (0.6, 0.4): sphere = (0.6 - 0.5, 0.4 - 0.5) = (0.1, -0.1)"""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)

    result = controller.process_frame(
        "PINCH", hand_x=0.6, hand_y=0.4
    )

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_offset_maintained_during_follow(controller):
    controller._sphere.x = 1.0
    controller._sphere.y = 0.5

    controller.process_frame("PINCH", hand_x=0.2, hand_y=0.3)

    # offset: dx = 1.0 - 0.2 = 0.8, dy = 0.5 - 0.3 = 0.2

    result = controller.process_frame(
        "PINCH", hand_x=0.4, hand_y=0.6
    )

    assert result.sphere_position.x == pytest.approx(1.2)
    assert result.sphere_position.y == pytest.approx(0.8)


# ─────────────────────────────────────────────
# OPEN_PALM → release
# ─────────────────────────────────────────────

def test_open_palm_releases_grab(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    result = controller.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)

    assert result.state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_release_preserves_last_position(controller):
    """After move, OPEN_PALM releases. Sphere keeps its last position."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.7, hand_y=0.3)

    # Sphere is now at (0.7 - 0.5, 0.3 - 0.5) = (0.2, -0.2)
    result = controller.process_frame("OPEN_PALM", hand_x=0.7, hand_y=0.3)

    assert result.sphere_position.x == pytest.approx(0.2)
    assert result.sphere_position.y == pytest.approx(-0.2)


# ─────────────────────────────────────────────
# Non-grab gestures from IDLE
# ─────────────────────────────────────────────

def test_point_from_idle_stays_idle(controller):
    result = controller.process_frame("POINT", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.IDLE


def test_fist_from_idle_stays_idle(controller):
    result = controller.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.IDLE


def test_relaxed_from_idle_stays_idle(controller):
    result = controller.process_frame("RELAXED", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.IDLE


def test_open_palm_from_idle_stays_idle(controller):
    result = controller.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.IDLE


# ─────────────────────────────────────────────
# Freeze while GRABBED
# ─────────────────────────────────────────────

def test_point_freezes_while_grabbed(controller):
    """POINT while GRABBED: sphere stays at last position, state stays GRABBED."""
    # Sphere at (0,0), grab at (0.5, 0.5), offset = (-0.5, -0.5)
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    # Move to (0.6, 0.4), sphere = (0.1, -0.1)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    # POINT at (0.8, 0.2) — sphere should freeze at (0.1, -0.1)
    result = controller.process_frame("POINT", hand_x=0.8, hand_y=0.2)

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_fist_freezes_while_grabbed(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    result = controller.process_frame("FIST", hand_x=0.8, hand_y=0.2)

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_relaxed_freezes_while_grabbed(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    result = controller.process_frame("RELAXED", hand_x=0.8, hand_y=0.2)

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_unknown_freezes_while_grabbed(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    result = controller.process_frame("UNKNOWN", hand_x=0.8, hand_y=0.2)

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_open_palm_while_grabbed_releases(controller):
    """OPEN_PALM while GRABBED releases. This is the only gesture that releases."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    result = controller.process_frame("OPEN_PALM", hand_x=0.8, hand_y=0.2)

    assert result.state == InteractionState.IDLE


# ─────────────────────────────────────────────
# PINCH resume after freeze
# ─────────────────────────────────────────────

def test_pinch_resumes_after_point_freeze(controller):
    """After freeze with POINT, PINCH resumes movement."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("POINT", hand_x=0.8, hand_y=0.2)

    # Sphere at (0,0), offset = (-0.5, -0.5)
    # PINCH at (0.9, 0.1): sphere = (0.9 - 0.5, 0.1 - 0.5) = (0.4, -0.4)
    result = controller.process_frame(
        "PINCH", hand_x=0.9, hand_y=0.1
    )

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.4)
    assert result.sphere_position.y == pytest.approx(-0.4)


def test_pinch_resumes_after_fist_freeze(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("FIST", hand_x=0.8, hand_y=0.2)

    result = controller.process_frame(
        "PINCH", hand_x=0.9, hand_y=0.1
    )

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.4)
    assert result.sphere_position.y == pytest.approx(-0.4)


def test_freeze_keeps_offset_after_resume(controller):
    """Freeze should not change the offset. Resume uses the same offset."""
    controller._sphere.x = 1.0
    controller._sphere.y = 0.5

    controller.process_frame("PINCH", hand_x=0.2, hand_y=0.3)
    # offset: dx = 1.0 - 0.2 = 0.8, dy = 0.5 - 0.3 = 0.2

    controller.process_frame("POINT", hand_x=0.5, hand_y=0.5)
    # frozen, offset still 0.8, 0.2

    result = controller.process_frame(
        "PINCH", hand_x=0.4, hand_y=0.6
    )

    assert result.sphere_position.x == pytest.approx(1.2)
    assert result.sphere_position.y == pytest.approx(0.8)


# ─────────────────────────────────────────────
# NO_HAND release
# ─────────────────────────────────────────────

def test_no_hand_releases_grab(controller):
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    result = controller.process_frame("NO_HAND")

    assert result.state == InteractionState.IDLE


def test_no_hand_preserves_position(controller):
    """NO_HAND releases but sphere keeps its last computed position."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.7, hand_y=0.3)

    # Sphere at (0.7 - 0.5, 0.3 - 0.5) = (0.2, -0.2)
    result = controller.process_frame("NO_HAND")

    assert result.sphere_position.x == pytest.approx(0.2)
    assert result.sphere_position.y == pytest.approx(-0.2)


def test_no_hand_from_idle_does_nothing(controller):
    result = controller.process_frame("NO_HAND")

    assert result.state == InteractionState.IDLE
    assert result.sphere_position.x == 0.0
    assert result.sphere_position.y == 0.0


# ─────────────────────────────────────────────
# Hand position tracking
# ─────────────────────────────────────────────

def test_hand_position_recorded_when_present(controller):
    result = controller.process_frame(
        "POINT", hand_x=0.4, hand_y=0.6
    )

    assert result.hand_position is not None
    assert result.hand_position.x == 0.4
    assert result.hand_position.y == 0.6


def test_hand_position_none_on_no_hand(controller):
    result = controller.process_frame("NO_HAND")

    assert result.hand_position is None


def test_hand_position_none_without_coords(controller):
    result = controller.process_frame("PINCH")

    assert result.hand_position is None


# ─────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────

def test_pinch_without_hand_does_not_grab(controller):
    """PINCH gesture with no hand coordinates should not grab."""
    result = controller.process_frame("PINCH")

    assert result.state == InteractionState.IDLE


def test_pinch_with_none_hand_coords_does_not_grab(controller):
    result = controller.process_frame(
        "PINCH", hand_x=None, hand_y=None
    )

    assert result.state == InteractionState.IDLE


def test_sphere_position_is_copy_not_reference(controller):
    """Sphere position returned is a snapshot, not a live reference."""
    result1 = controller.process_frame(
        "PINCH", hand_x=0.5, hand_y=0.5
    )
    result2 = controller.process_frame(
        "PINCH", hand_x=0.6, hand_y=0.4
    )

    # Frame 1: sphere stays at origin (offset prevents jump)
    assert result1.sphere_position.x == pytest.approx(0.0)
    assert result1.sphere_position.y == pytest.approx(0.0)
    # Frame 2: sphere moves to hand + offset
    assert result2.sphere_position.x == pytest.approx(0.1)
    assert result2.sphere_position.y == pytest.approx(-0.1)


def test_multiple_grab_release_cycles(controller):
    """Verify the controller works across multiple grab-release cycles."""
    # Cycle 1: sphere at (0,0), grab at (0.3, 0.4), offset=(-0.3, -0.4)
    controller.process_frame("PINCH", hand_x=0.3, hand_y=0.4)
    # Move to (0.5, 0.5), sphere = (0.5-0.3, 0.5-0.4) = (0.2, 0.1)
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("OPEN_PALM")

    # Cycle 2: sphere at (0.2, 0.1), grab at (0.1, 0.2), offset=(0.1, -0.1)
    controller.process_frame("PINCH", hand_x=0.1, hand_y=0.2)
    # Move to (0.2, 0.3), sphere = (0.2+0.1, 0.3-0.1) = (0.3, 0.2)
    controller.process_frame("PINCH", hand_x=0.2, hand_y=0.3)

    result = controller.process_frame("OPEN_PALM")
    assert result.state == InteractionState.IDLE
    assert result.sphere_position.x == pytest.approx(0.3)
    assert result.sphere_position.y == pytest.approx(0.2)


def test_freeze_does_not_consume_offset(controller):
    """Freezing (non-grab gesture) should not modify the offset."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    dx = controller._offset.dx
    dy = controller._offset.dy

    controller.process_frame("FIST", hand_x=0.9, hand_y=0.9)

    assert controller._offset.dx == dx
    assert controller._offset.dy == dy


def test_grab_from_nonzero_sphere_then_move(controller):
    """Full sequence: set sphere, grab, move, verify."""
    # Place sphere at known position
    controller._sphere.x = 2.0
    controller._sphere.y = 1.0

    # Grab at (0.5, 0.3): offset = (1.5, 0.7)
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.3)
    assert controller._offset.dx == pytest.approx(1.5)
    assert controller._offset.dy == pytest.approx(0.7)

    # Move hand to (0.8, 0.6): sphere = (0.8+1.5, 0.6+0.7) = (2.3, 1.3)
    result = controller.process_frame("PINCH", hand_x=0.8, hand_y=0.6)
    assert result.sphere_position.x == pytest.approx(2.3)
    assert result.sphere_position.y == pytest.approx(1.3)


def test_freeze_prevents_movement_across_multiple_frames(controller):
    """Multiple consecutive freeze frames should keep sphere frozen."""
    controller.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    controller.process_frame("PINCH", hand_x=0.6, hand_y=0.4)

    for _ in range(5):
        result = controller.process_frame("FIST", hand_x=0.9, hand_y=0.9)

    assert result.state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)
