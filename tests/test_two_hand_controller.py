"""Tests for V1.6 Two-Hand Interaction Controller.

Comprehensive tests for:
  - TwoHandController basic state management
  - Single-hand backward compatibility (V1.4 behavior preserved)
  - Two-hand grab / release
  - Two-hand cooperative sphere positioning
  - Two-hand scaling based on distance
  - Two-hand rotation based on angle
  - Per-hand independence (no fighting)
  - Safe handling when one hand disappears
  - Hand-dominance / tie-breaking
  - TwoHandEventDetector per-hand event attribution
  - Edge cases

All tests use mocked landmarks — no physical webcam required.
"""

import math

import pytest

from backend.interaction.controller import (
    GrabOffset,
    HandLabel,
    HandPosition,
    InteractionState,
    PerHandState,
    SphereStateExtended,
    SpatialInteractionController,
    TwoHandController,
    TwoHandResult,
)
from backend.interaction.event_detector import (
    TwoHandEventDetector,
)
from backend.interaction.events import EventType, InteractionEvent


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def two_hand():
    """Return a fresh TwoHandController."""
    return TwoHandController()


@pytest.fixture
def two_detector():
    """Return a fresh TwoHandEventDetector."""
    return TwoHandEventDetector()


# ─────────────────────────────────────────────
# Basic state
# ─────────────────────────────────────────────

def test_initial_state_is_idle(two_hand):
    result = two_hand.process_frame()
    assert result.interaction_state == "IDLE"


def test_initial_sphere_at_origin(two_hand):
    result = two_hand.process_frame()
    assert result.sphere_position.x == 0.0
    assert result.sphere_position.y == 0.0


def test_initial_scale_is_one(two_hand):
    result = two_hand.process_frame()
    assert result.sphere_position.scale == 1.0


def test_initial_rotation_is_zero(two_hand):
    result = two_hand.process_frame()
    assert result.sphere_position.rotation == 0.0


def test_initial_hand_states_are_idle(two_hand):
    result = two_hand.process_frame()
    assert result.left_state == InteractionState.IDLE
    assert result.right_state == InteractionState.IDLE


# ─────────────────────────────────────────────
# Single-hand left (V1.4 backward compat)
# ─────────────────────────────────────────────

def test_left_pinch_grabs_from_idle(two_hand):
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.interaction_state == "GRABBED"


def test_left_grab_sphere_stays_at_origin(two_hand):
    """Sphere should NOT jump on grab (V1.4 behavior)."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4
    )
    assert result.sphere_position.x == 0.0
    assert result.sphere_position.y == 0.0


def test_left_sphere_follows_hand(two_hand):
    """After grab, sphere = hand + offset."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4
    )
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


def test_left_open_palm_releases(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    result = two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.5, left_y=0.5
    )
    assert result.left_state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_left_no_hand_releases(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    result = two_hand.process_frame(
        left_gesture="NO_HAND"
    )
    assert result.left_state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_left_freeze_while_grabbed(two_hand):
    """POINT while GRABBED freezes sphere."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4
    )
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.8, left_y=0.2
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(-0.1)


# ─────────────────────────────────────────────
# Single-hand right (mirror of left)
# ─────────────────────────────────────────────

def test_right_pinch_grabs_from_idle(two_hand):
    result = two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3
    )
    assert result.right_state == InteractionState.GRABBED
    assert result.interaction_state == "GRABBED"


def test_right_sphere_follows_hand(two_hand):
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.5, right_y=0.5
    )
    result = two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3
    )
    assert result.sphere_position.x == pytest.approx(0.2)
    assert result.sphere_position.y == pytest.approx(-0.2)


def test_right_open_palm_releases(two_hand):
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.5, right_y=0.5
    )
    result = two_hand.process_frame(
        right_gesture="OPEN_PALM", right_x=0.5, right_y=0.5
    )
    assert result.right_state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_right_no_hand_releases(two_hand):
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.5, right_y=0.5
    )
    result = two_hand.process_frame(
        right_gesture="NO_HAND"
    )
    assert result.right_state == InteractionState.IDLE


# ─────────────────────────────────────────────
# Independent per-hand tracking
# ─────────────────────────────────────────────

def test_independent_hand_states(two_hand):
    """Left grabs, right stays idle."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.5
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.IDLE


def test_left_grab_does_not_affect_right(two_hand):
    """Grabbing with left should not change right state."""
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.4,
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.GRABBED


def test_right_release_does_not_affect_left(two_hand):
    """Releasing right should not release left."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4
    )
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.5,
        right_gesture="OPEN_PALM", right_x=0.7, right_y=0.3,
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.IDLE


# ─────────────────────────────────────────────
# Two-hand grab
# ─────────────────────────────────────────────

def test_simultaneous_grab(two_hand):
    """Both hands pinch simultaneously."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.GRABBED
    assert result.interaction_state == "TWO_HAND"


def test_staggered_grab_right_joins_later(two_hand):
    """Left grabs first, then right joins."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.interaction_state == "TWO_HAND"


def test_staggered_grab_left_joins_later(two_hand):
    """Right grabs first, then left joins."""
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.5
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.interaction_state == "TWO_HAND"


# ─────────────────────────────────────────────
# Two-hand cooperative positioning
# ─────────────────────────────────────────────

def test_two_hand_sphere_at_midpoint(two_hand):
    """Two-hand grab preserves sphere position (no-jump offset).
    Sphere starts at origin; offset = origin - midpoint = (-0.5, -0.5).
    Sphere stays at origin on first frame (no jump)."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Sphere stays at (0, 0) — no jump on grab (V1.4 behavior)
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)


def test_two_hand_sphere_follows_midpoint(two_hand):
    """Sphere follows midpoint as hands move.
    Offset captured at (0,0) - midpoint(0.5,0.5) = (-0.5, -0.5).
    On frame 2, midpoint shifts to (0.6, 0.5), sphere = (0.1, 0).
    Delta: sphere moved same as midpoint (+0.1, 0)."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.4,
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    assert result.sphere_position.x == pytest.approx(0.1)
    assert result.sphere_position.y == pytest.approx(0.0)


def test_two_hand_sphere_from_nonzero_position(two_hand):
    """Sphere offset preserved from previous position."""
    two_hand._sphere.x = 2.0
    two_hand._sphere.y = 1.0

    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # midpoint = (0.5, 0.5), offset = (2.0-0.5, 1.0-0.5) = (1.5, 0.5)
    assert result.sphere_position.x == pytest.approx(2.0)
    assert result.sphere_position.y == pytest.approx(1.0)


# ─────────────────────────────────────────────
# Two-hand scaling
# ─────────────────────────────────────────────

def test_two_hand_scale_stays_one_at_initial_distance(two_hand):
    """Scale starts at 1.0 when hands are at initial distance."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.sphere_position.scale == pytest.approx(1.0)


def test_two_hand_scale_increases_when_hands_apart(two_hand):
    """Moving hands apart increases scale."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Initial distance was 0.4 (from 0.3 to 0.7). Move to distance 0.8.
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.1, left_y=0.5,
        right_gesture="PINCH", right_x=0.9, right_y=0.5,
    )
    assert result.sphere_position.scale == pytest.approx(2.0)


def test_two_hand_scale_decreases_when_hands_closer(two_hand):
    """Moving hands closer decreases scale."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Distance was 0.4. Now move to distance 0.2.
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.5,
        right_gesture="PINCH", right_x=0.6, right_y=0.5,
    )
    assert result.sphere_position.scale == pytest.approx(0.5)


def test_two_hand_scale_clamped_max(two_hand):
    """Scale clamped to max 4.0."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Move very far apart
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.0, left_y=0.5,
        right_gesture="PINCH", right_x=1.0, right_y=0.5,
    )
    assert result.sphere_position.scale <= 4.0


def test_two_hand_scale_clamped_min(two_hand):
    """Scale clamped to min 0.25."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Move very close
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.49, left_y=0.5,
        right_gesture="PINCH", right_x=0.51, right_y=0.5,
    )
    assert result.sphere_position.scale >= 0.25


def test_two_hand_scale_resets_on_release(two_hand):
    """Scale resets to 1.0 when one hand releases."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.1, left_y=0.5,
        right_gesture="PINCH", right_x=0.9, right_y=0.5,
    )
    result = two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.1, left_y=0.5,
        right_gesture="PINCH", right_x=0.9, right_y=0.5,
    )
    assert result.sphere_position.scale == 1.0


# ─────────────────────────────────────────────
# Two-hand rotation
# ─────────────────────────────────────────────

def test_two_hand_rotation_zero_at_start(two_hand):
    """Rotation starts at 0."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.sphere_position.rotation == pytest.approx(0.0)


def test_two_hand_rotation_changes_with_angle(two_hand):
    """Rotation follows angle change between hands."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Initial angle = atan2(0, 0.4) = 0
    # Now rotate right hand upward: angle = atan2(-0.2, 0.4)
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.3,
    )
    expected_angle = math.atan2(-0.2, 0.4)
    assert result.sphere_position.rotation == pytest.approx(expected_angle)


def test_two_hand_rotation_resets_on_release(two_hand):
    """Rotation resets to 0 when transitioning out of two-hand."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.3,
    )
    result = two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.3,
    )
    assert result.sphere_position.rotation == 0.0


# ─────────────────────────────────────────────
# Fighting prevention: per-hand independence
# ─────────────────────────────────────────────

def test_left_release_does_not_corrupt_right_state(two_hand):
    """Left releasing must not affect right's sphere position."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Both hands moved (symmetrically: midpoint stays at 0.5, 0.5)
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.2, left_y=0.4,
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    # Sphere at midpoint + offset = (0.5-0.5, 0.5-0.5) = (0, 0)
    # Left releases
    result = two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.2, left_y=0.4,
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    # Right should continue grabbing without jump
    assert result.right_state == InteractionState.GRABBED
    assert result.left_state == InteractionState.IDLE
    # Sphere stays at (0, 0) — same position as before release
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)


def test_right_release_does_not_corrupt_left_state(two_hand):
    """Right releasing must not affect left's sphere position."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Move both hands (symmetrically)
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.2, left_y=0.4,
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    # Sphere at (0, 0). Right releases.
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.2, left_y=0.4,
        right_gesture="OPEN_PALM", right_x=0.8, right_y=0.6,
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.IDLE
    # Sphere stays at (0, 0) — no jump
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)


# ─────────────────────────────────────────────
# Safe handling when one hand disappears
# ─────────────────────────────────────────────

def test_left_no_hand_right_continues(two_hand):
    """Left hand disappears, right continues grabbing."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Left disappears
    result = two_hand.process_frame(
        left_gesture="NO_HAND",
        right_gesture="PINCH", right_x=0.8, right_y=0.4,
    )
    assert result.left_state == InteractionState.IDLE
    assert result.right_state == InteractionState.GRABBED
    assert result.interaction_state == "GRABBED"
    # Sphere stays at two-hand midpoint (no jump)
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)
    # Scale and rotation reset
    assert result.sphere_position.scale == 1.0
    assert result.sphere_position.rotation == 0.0


def test_right_no_hand_left_continues(two_hand):
    """Right hand disappears, left continues grabbing."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Right disappears
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.4,
        right_gesture="NO_HAND",
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.IDLE
    assert result.interaction_state == "GRABBED"


def test_both_hands_disappear(two_hand):
    """Both hands disappear simultaneously."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    result = two_hand.process_frame(
        left_gesture="NO_HAND",
        right_gesture="NO_HAND",
    )
    assert result.left_state == InteractionState.IDLE
    assert result.right_state == InteractionState.IDLE
    assert result.interaction_state == "IDLE"


def test_one_hand_disappears_and_returns(two_hand):
    """Left disappears then returns. Right stays grabbed throughout."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Left disappears
    two_hand.process_frame(
        left_gesture="NO_HAND",
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Left returns and grabs
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.interaction_state == "TWO_HAND"
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.GRABBED


def test_no_sphere_jump_on_hand_disappear(two_hand):
    """Sphere should not jump when one hand disappears."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.2, left_y=0.4,
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    # Sphere is at midpoint + offset = (0.5, 0.5) + (-0.5, -0.5) = (0, 0)
    # Left disappears
    result = two_hand.process_frame(
        left_gesture="NO_HAND",
        right_gesture="PINCH", right_x=0.8, right_y=0.6,
    )
    # Sphere stays at (0, 0) — no jump
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)


# ─────────────────────────────────────────────
# Hand-dominance / tie-breaking
# ─────────────────────────────────────────────

def test_both_hands_simultaneous_grab_no_conflict(two_hand):
    """Simultaneous grab from both hands enters TWO_HAND directly."""
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    assert result.interaction_state == "TWO_HAND"
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.GRABBED


def test_event_ordering_left_before_right(two_hand):
    """When both grab simultaneously, events appear in order."""
    det = TwoHandEventDetector()
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    events = det.process(
        result,
        left_gesture="PINCH",
        right_gesture="PINCH",
    )
    grab_events = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_events) == 2
    assert grab_events[0].hand_label == "LEFT"
    assert grab_events[1].hand_label == "RIGHT"


# ─────────────────────────────────────────────
# Non-grab gestures
# ─────────────────────────────────────────────

def test_point_from_idle_stays_idle(two_hand):
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.5, left_y=0.5
    )
    assert result.left_state == InteractionState.IDLE


def test_fist_from_idle_stays_idle(two_hand):
    result = two_hand.process_frame(
        right_gesture="FIST", right_x=0.5, right_y=0.5
    )
    assert result.right_state == InteractionState.IDLE


def test_open_palm_from_idle_stays_idle(two_hand):
    result = two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.5, left_y=0.5
    )
    assert result.left_state == InteractionState.IDLE


# ─────────────────────────────────────────────
# Freeze in two-hand mode
# ─────────────────────────────────────────────

def test_freeze_one_hand_in_two_hand_mode(two_hand):
    """One hand freezes, other continues. Sphere follows non-frozen hand."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Left freezes (FIST), right still PINCH
    result = two_hand.process_frame(
        left_gesture="FIST", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.8, right_y=0.4,
    )
    assert result.left_state == InteractionState.GRABBED
    assert result.right_state == InteractionState.GRABBED
    assert result.interaction_state == "TWO_HAND"


def test_both_freeze_in_two_hand_mode(two_hand):
    """Both hands freeze, sphere stays at last position."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Sphere at (0, 0) with offset (-0.5, -0.5)
    two_hand.process_frame(
        left_gesture="FIST", left_x=0.3, left_y=0.5,
        right_gesture="FIST", right_x=0.7, right_y=0.5,
    )
    # Both frozen — sphere stays
    result = two_hand.process_frame(
        left_gesture="FIST", left_x=0.3, left_y=0.5,
        right_gesture="FIST", right_x=0.7, right_y=0.5,
    )
    assert result.sphere_position.x == pytest.approx(0.0)
    assert result.sphere_position.y == pytest.approx(0.0)


# ─────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────

def test_pinch_without_coords_does_not_grab(two_hand):
    """PINCH without hand coordinates should not grab."""
    result = two_hand.process_frame(
        left_gesture="PINCH",
        right_gesture="PINCH",
    )
    assert result.left_state == InteractionState.IDLE
    assert result.right_state == InteractionState.IDLE


def test_none_hand_coords_do_not_grab(two_hand):
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=None, left_y=None,
        right_gesture="PINCH", right_x=None, right_y=None,
    )
    assert result.left_state == InteractionState.IDLE
    assert result.right_state == InteractionState.IDLE


def test_sphere_position_is_snapshot(two_hand):
    """Sphere position returned is a snapshot."""
    result1 = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    result2 = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4
    )
    assert result1.sphere_position.x == pytest.approx(0.0)
    assert result1.sphere_position.y == pytest.approx(0.0)
    assert result2.sphere_position.x == pytest.approx(0.1)
    assert result2.sphere_position.y == pytest.approx(-0.1)


def test_multiple_two_hand_cycles(two_hand):
    """Multiple grab-release-regrab cycles work correctly."""
    # Two-hand grab
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Both release
    two_hand.process_frame(
        left_gesture="OPEN_PALM", left_x=0.3, left_y=0.5,
        right_gesture="OPEN_PALM", right_x=0.7, right_y=0.5,
    )
    # Grab again
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.4,
        right_gesture="PINCH", right_x=0.6, right_y=0.6,
    )
    assert result.interaction_state == "TWO_HAND"


def test_left_hand_position_recorded(two_hand):
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.4, left_y=0.6
    )
    assert result.left_hand is not None
    assert result.left_hand.x == 0.4
    assert result.left_hand.y == 0.6


def test_right_hand_position_recorded(two_hand):
    result = two_hand.process_frame(
        right_gesture="POINT", right_x=0.7, right_y=0.3
    )
    assert result.right_hand is not None
    assert result.right_hand.x == 0.7
    assert result.right_hand.y == 0.3


def test_hand_position_none_on_no_hand(two_hand):
    result = two_hand.process_frame(
        left_gesture="NO_HAND",
        right_gesture="NO_HAND",
    )
    assert result.left_hand is None
    assert result.right_hand is None


def test_scale_zero_distance_clamped(two_hand):
    """Hands at same position: distance near zero, scale clamped."""
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # Move both hands to same point
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5,
        right_gesture="PINCH", right_x=0.5, right_y=0.5,
    )
    assert result.sphere_position.scale >= 0.25


def test_two_hand_offset_preserved_during_follow(two_hand):
    """Two-hand offset prevents sphere jump."""
    two_hand._sphere.x = 3.0
    two_hand._sphere.y = 2.0

    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    # midpoint = (0.5, 0.5), offset = (3.0-0.5, 2.0-0.5) = (2.5, 1.5)
    assert result.sphere_position.x == pytest.approx(3.0)
    assert result.sphere_position.y == pytest.approx(2.0)


# ─────────────────────────────────────────────
# TwoHandEventDetector tests
# ─────────────────────────────────────────────

def test_detector_grab_events_per_hand(two_detector):
    """Both hands grab → two GRAB events with labels."""
    ctrl = TwoHandController()
    result = ctrl.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    events = two_detector.process(
        result,
        left_gesture="PINCH",
        right_gesture="PINCH",
    )
    grabs = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grabs) == 2
    labels = [e.hand_label for e in grabs]
    assert "LEFT" in labels
    assert "RIGHT" in labels


def test_detector_release_events_per_hand(two_detector):
    """Both hands release → two RELEASE events."""
    ctrl = TwoHandController()
    ctrl.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5,
        right_gesture="PINCH", right_x=0.7, right_y=0.5,
    )
    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.3, left_y=0.5,
            right_gesture="PINCH", right_x=0.7, right_y=0.5,
        ),
        left_gesture="PINCH",
        right_gesture="PINCH",
    )
    result = ctrl.process_frame(
        left_gesture="OPEN_PALM", left_x=0.3, left_y=0.5,
        right_gesture="OPEN_PALM", right_x=0.7, right_y=0.5,
    )
    events = two_detector.process(
        result,
        left_gesture="OPEN_PALM",
        right_gesture="OPEN_PALM",
    )
    releases = [e for e in events if e.event_type == EventType.RELEASE]
    assert len(releases) == 2


def test_detector_click_per_hand(two_detector):
    """Quick grab+release on left hand → CLICK event with LEFT label."""
    ctrl = TwoHandController()
    ctrl.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )
    result = ctrl.process_frame(
        left_gesture="OPEN_PALM", left_x=0.5, left_y=0.5
    )
    events = two_detector.process(
        result,
        left_gesture="OPEN_PALM",
    )
    clicks = [e for e in events if e.event_type == EventType.CLICK]
    assert len(clicks) == 1
    assert clicks[0].hand_label == "LEFT"


def test_detector_freeze_per_hand(two_detector):
    """FREEZE event attributed to correct hand."""
    ctrl = TwoHandController()
    ctrl.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )
    result = ctrl.process_frame(
        left_gesture="FIST", left_x=0.5, left_y=0.5
    )
    events = two_detector.process(
        result,
        left_gesture="FIST",
    )
    freezes = [e for e in events if e.event_type == EventType.FREEZE]
    assert len(freezes) == 1
    assert freezes[0].hand_label == "LEFT"


def test_detector_independent_per_hand(two_detector):
    """Left click does not produce events for right hand."""
    ctrl = TwoHandController()
    ctrl.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )
    result = ctrl.process_frame(
        left_gesture="OPEN_PALM", left_x=0.5, left_y=0.5
    )
    events = two_detector.process(
        result,
        left_gesture="OPEN_PALM",
    )
    right_events = [e for e in events if e.hand_label == "RIGHT"]
    assert len(right_events) == 0


def test_detector_frame_counter(two_detector):
    """Frame counter advances per process call."""
    ctrl = TwoHandController()
    assert two_detector.frame == 0

    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )
    assert two_detector.frame == 1

    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )
    assert two_detector.frame == 2


def test_detector_events_empty_when_nothing_happens(two_detector):
    ctrl = TwoHandController()
    result = ctrl.process_frame(
        left_gesture="UNKNOWN", left_x=0.5, left_y=0.5
    )
    events = two_detector.process(
        result,
        left_gesture="UNKNOWN",
    )
    assert len(events) == 0


def test_detector_does_not_modify_controller(two_detector):
    """EventDetector must be purely observational."""
    ctrl = TwoHandController()
    ctrl.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5
    )
    state_before = ctrl.sphere_position.x
    sphere_before = (
        ctrl.sphere_position.x,
        ctrl.sphere_position.y,
    )

    two_detector.process(
        ctrl.process_frame(
            left_gesture="PINCH", left_x=0.5, left_y=0.5
        ),
        left_gesture="PINCH",
    )

    assert (ctrl.sphere_position.x, ctrl.sphere_position.y) == sphere_before


# ─────────────────────────────────────────────
# InteractionEvent backward compat
# ─────────────────────────────────────────────

def test_event_hand_label_default_none():
    """Events created without hand_label have None."""
    event = InteractionEvent(
        event_type=EventType.GRAB,
        timestamp=1,
    )
    assert event.hand_label is None


def test_event_hand_label_set():
    event = InteractionEvent(
        event_type=EventType.GRAB,
        timestamp=1,
        hand_label="LEFT",
    )
    assert event.hand_label == "LEFT"


# ─────────────────────────────────────────────
# SpatialInteractionController unchanged
# ─────────────────────────────────────────────

def test_old_controller_still_works():
    """V1.4 SpatialInteractionController is preserved."""
    ctrl = SpatialInteractionController()
    result = ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.GRABBED
    result = ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    assert result.state == InteractionState.IDLE


# ─────────────────────────────────────────────
# V1.7: Z-axis / depth tests
# ─────────────────────────────────────────────

def test_initial_sphere_z_is_zero(two_hand):
    result = two_hand.process_frame()
    assert result.sphere_position.z == 0.0


def test_left_hand_z_recorded(two_hand):
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.4, left_y=0.6, left_z=-1.5
    )
    assert result.left_hand is not None
    assert result.left_hand.z == -1.5


def test_right_hand_z_recorded(two_hand):
    result = two_hand.process_frame(
        right_gesture="POINT", right_x=0.7, right_y=0.3, right_z=-2.0
    )
    assert result.right_hand is not None
    assert result.right_hand.z == -2.0


def test_hand_z_defaults_to_zero(two_hand):
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.4, left_y=0.6
    )
    assert result.left_hand is not None
    assert result.left_hand.z == 0.0


def test_left_sphere_follows_hand_z(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5, left_z=-1.0
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4, left_z=-2.0
    )
    assert result.sphere_position.z == pytest.approx(-1.0)


def test_right_sphere_follows_hand_z(two_hand):
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.5, right_y=0.5, right_z=-1.0
    )
    result = two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3, right_z=-2.0
    )
    assert result.sphere_position.z == pytest.approx(-1.0)


def test_two_hand_z_follows_midpoint(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5, left_z=-1.0,
        right_gesture="PINCH", right_x=0.7, right_y=0.5, right_z=-3.0,
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.4, left_y=0.4, left_z=-2.0,
        right_gesture="PINCH", right_x=0.8, right_y=0.6, right_z=-4.0,
    )
    # midpoint_z = (-2.0 + -4.0) / 2 = -3.0
    # offset_z = 0.0 - (-2.0) = 2.0 (initial midpoint_z = (-1+-3)/2 = -2.0)
    assert result.sphere_position.z == pytest.approx(-1.0)


def test_two_hand_z_from_nonzero_position(two_hand):
    two_hand._sphere.z = 5.0
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5, left_z=-1.0,
        right_gesture="PINCH", right_x=0.7, right_y=0.5, right_z=-3.0,
    )
    # midpoint_z = -2.0, offset_z = 5.0 - (-2.0) = 7.0
    assert result.sphere_position.z == pytest.approx(5.0)


def test_freeze_preserves_z_in_single_hand(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5, left_z=-1.0
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4, left_z=-2.0
    )
    result = two_hand.process_frame(
        left_gesture="POINT", left_x=0.8, left_y=0.2, left_z=-5.0
    )
    assert result.sphere_position.z == pytest.approx(-1.0)


def test_two_hand_offset_z_captured(two_hand):
    two_hand._sphere.z = 4.0
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5, left_z=-1.0,
        right_gesture="PINCH", right_x=0.7, right_y=0.5, right_z=-3.0,
    )
    assert two_hand._two_hand_offset.dz == pytest.approx(6.0)


def test_left_grab_does_not_affect_right_z(two_hand):
    """Left grabbing should not change right's z handling."""
    two_hand.process_frame(
        right_gesture="PINCH", right_x=0.7, right_y=0.3, right_z=-2.0
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.4, left_z=-1.0,
        right_gesture="PINCH", right_x=0.7, right_y=0.4, right_z=-3.0,
    )
    assert two_hand._hands[HandLabel.RIGHT].hand is not None
    assert two_hand._hands[HandLabel.RIGHT].hand.z == -3.0


def test_single_hand_z_from_nonzero_sphere(two_hand):
    two_hand._sphere.z = 3.0
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5, left_z=-1.0
    )
    result = two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4, left_z=-2.0
    )
    # offset.dz = 3.0 - (-1.0) = 4.0; sphere.z = -2.0 + 4.0 = 2.0
    assert result.sphere_position.z == pytest.approx(2.0)


def test_no_hand_releases_preserves_z(two_hand):
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.5, left_y=0.5, left_z=-1.0
    )
    two_hand.process_frame(
        left_gesture="PINCH", left_x=0.6, left_y=0.4, left_z=-2.0
    )
    result = two_hand.process_frame(left_gesture="NO_HAND")
    assert result.sphere_position.z == pytest.approx(-1.0)


def test_event_detector_captures_z(two_detector):
    """TwoHandEventDetector events carry hand_z."""
    ctrl = TwoHandController()
    result = ctrl.process_frame(
        left_gesture="PINCH", left_x=0.3, left_y=0.5, left_z=-1.5,
    )
    events = two_detector.process(
        result, left_gesture="PINCH",
    )
    grabs = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grabs) == 1
    assert grabs[0].hand_z == -1.5
