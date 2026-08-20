"""Tests for the interaction event system.

Covers:
  - EventType enum values
  - InteractionEvent immutability and fields
  - EventDetector GRAB/RELEASE events
  - EventDetector CLICK detection
  - EventDetector DOUBLE_CLICK detection
  - EventDetector FREEZE/RESUME events
  - Edge cases (no hand, multiple grabs, long grabs)
"""

import pytest

from backend.interaction.controller import (
    SpatialInteractionController,
)
from backend.interaction.event_detector import EventDetector
from backend.interaction.events import EventType, InteractionEvent


# ─────────────────────────────────────────────
# EventType enum
# ─────────────────────────────────────────────

def test_event_type_values():
    assert EventType.GRAB.value == "GRAB"
    assert EventType.RELEASE.value == "RELEASE"
    assert EventType.CLICK.value == "CLICK"
    assert EventType.DOUBLE_CLICK.value == "DOUBLE_CLICK"
    assert EventType.FREEZE.value == "FREEZE"
    assert EventType.RESUME.value == "RESUME"


def test_event_type_count():
    assert len(EventType) == 6


# ─────────────────────────────────────────────
# InteractionEvent
# ─────────────────────────────────────────────

def test_event_is_frozen():
    event = InteractionEvent(
        event_type=EventType.GRAB,
        timestamp=1,
        hand_x=0.5,
        hand_y=0.5,
    )
    with pytest.raises(AttributeError):
        event.event_type = EventType.RELEASE


def test_event_default_position():
    event = InteractionEvent(
        event_type=EventType.CLICK,
        timestamp=5,
    )
    assert event.hand_x == 0.0
    assert event.hand_y == 0.0


# ─────────────────────────────────────────────
# EventDetector: GRAB / RELEASE
# ─────────────────────────────────────────────
#
# NOTE: The event detector observes the controller state.
# The controller must be updated BEFORE the detector runs.
# In main.py: controller.process_frame() then detector.process().
# Tests follow this same pattern.

def test_grab_event_emitted():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    events = det.process("PINCH", ctrl, 0.5, 0.5)

    grab_ev = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_ev) == 1


def test_grab_event_has_hand_position():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.3, hand_y=0.4)
    events = det.process("PINCH", ctrl, 0.3, 0.4)

    grab_ev = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_ev) == 1
    assert grab_ev[0].hand_x == 0.3
    assert grab_ev[0].hand_y == 0.4


def test_release_event_emitted():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    release_ev = [e for e in events if e.event_type == EventType.RELEASE]
    assert len(release_ev) == 1


def test_no_grab_event_when_idle():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("POINT", hand_x=0.5, hand_y=0.5)
    events = det.process("POINT", ctrl, 0.5, 0.5)

    grab_ev = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_ev) == 0


def test_no_release_when_not_grabbed():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    release_ev = [e for e in events if e.event_type == EventType.RELEASE]
    assert len(release_ev) == 0


def test_grab_release_cycle():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("PINCH", hand_x=0.6, hand_y=0.4)
    det.process("PINCH", ctrl, 0.6, 0.4)

    ctrl.process_frame("OPEN_PALM", hand_x=0.6, hand_y=0.4)
    events = det.process("OPEN_PALM", ctrl, 0.6, 0.4)

    types = [e.event_type for e in events]
    assert EventType.RELEASE in types


# ─────────────────────────────────────────────
# EventDetector: CLICK detection
# ─────────────────────────────────────────────

def test_quick_grab_release_is_click():
    det = EventDetector(click_window=12)
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    click_ev = [e for e in events if e.event_type == EventType.CLICK]
    assert len(click_ev) == 1


def test_long_grab_is_not_click():
    det = EventDetector(click_window=12)
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    for i in range(15):
        ctrl.process_frame("PINCH", hand_x=0.5 + i * 0.01, hand_y=0.5)
        det.process("PINCH", ctrl, 0.5 + i * 0.01, 0.5)

    ctrl.process_frame("OPEN_PALM", hand_x=0.7, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.7, 0.5)

    click_ev = [e for e in events if e.event_type == EventType.CLICK]
    assert len(click_ev) == 0


def test_click_at_boundary_of_window():
    det = EventDetector(click_window=5)
    ctrl = SpatialInteractionController()

    # Grab at frame 1. With click_window=5, release must happen
    # at frame 6 or earlier (duration = release_frame - grab_start_frame <= 5).
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)  # frame 1: GRAB, grab_start=1

    for _ in range(4):  # frames 2-5: still GRABBED
        ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
        det.process("PINCH", ctrl, 0.5, 0.5)

    # Frame 6: release. Duration = 6 - 1 = 5 <= 5 → click
    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    click_ev = [e for e in events if e.event_type == EventType.CLICK]
    assert len(click_ev) == 1


def test_click_beyond_boundary_is_not_click():
    det = EventDetector(click_window=5)
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    for _ in range(6):
        ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
        det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    events = det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    click_ev = [e for e in events if e.event_type == EventType.CLICK]
    assert len(click_ev) == 0


# ─────────────────────────────────────────────
# EventDetector: DOUBLE_CLICK detection
# ─────────────────────────────────────────────

def test_double_click_detected():
    det = EventDetector(click_window=12, double_click_window=40)
    ctrl = SpatialInteractionController()

    # First click
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    # Second click within window
    ctrl.process_frame("PINCH", hand_x=0.6, hand_y=0.6)
    det.process("PINCH", ctrl, 0.6, 0.6)
    ctrl.process_frame("OPEN_PALM", hand_x=0.6, hand_y=0.6)
    events = det.process("OPEN_PALM", ctrl, 0.6, 0.6)

    dc_ev = [e for e in events if e.event_type == EventType.DOUBLE_CLICK]
    assert len(dc_ev) == 1


def test_double_click_not_detected_outside_window():
    det = EventDetector(click_window=12, double_click_window=10)
    ctrl = SpatialInteractionController()

    # First click
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    # Wait beyond window
    for _ in range(15):
        ctrl.process_frame("UNKNOWN", hand_x=0.5, hand_y=0.5)
        det.process("UNKNOWN", ctrl, 0.5, 0.5)

    # Second click — too late
    ctrl.process_frame("PINCH", hand_x=0.6, hand_y=0.6)
    det.process("PINCH", ctrl, 0.6, 0.6)
    ctrl.process_frame("OPEN_PALM", hand_x=0.6, hand_y=0.6)
    events = det.process("OPEN_PALM", ctrl, 0.6, 0.6)

    dc_ev = [e for e in events if e.event_type == EventType.DOUBLE_CLICK]
    assert len(dc_ev) == 0


def test_double_click_at_boundary():
    det = EventDetector(click_window=5, double_click_window=10)
    ctrl = SpatialInteractionController()

    # First click: GRAB at frame 1, RELEASE at frame 2 → CLICK at frame 2
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    # 8 frames later (frames 3-10). Second click at frame 11.
    # 11 - 2 = 9 <= 10 → double-click at boundary.
    for _ in range(8):
        ctrl.process_frame("UNKNOWN", hand_x=0.5, hand_y=0.5)
        det.process("UNKNOWN", ctrl, 0.5, 0.5)

    # Second click
    ctrl.process_frame("PINCH", hand_x=0.6, hand_y=0.6)
    det.process("PINCH", ctrl, 0.6, 0.6)
    ctrl.process_frame("OPEN_PALM", hand_x=0.6, hand_y=0.6)
    events = det.process("OPEN_PALM", ctrl, 0.6, 0.6)

    dc_ev = [e for e in events if e.event_type == EventType.DOUBLE_CLICK]
    assert len(dc_ev) == 1


# ─────────────────────────────────────────────
# EventDetector: FREEZE / RESUME
# ─────────────────────────────────────────────

def test_freeze_event_emitted():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    events = det.process("FIST", ctrl, 0.5, 0.5)

    freeze_ev = [e for e in events if e.event_type == EventType.FREEZE]
    assert len(freeze_ev) == 1


def test_resume_event_emitted():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    det.process("FIST", ctrl, 0.5, 0.5)

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    events = det.process("PINCH", ctrl, 0.5, 0.5)

    resume_ev = [e for e in events if e.event_type == EventType.RESUME]
    assert len(resume_ev) == 1


def test_no_freeze_when_idle():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    events = det.process("FIST", ctrl, 0.5, 0.5)

    freeze_ev = [e for e in events if e.event_type == EventType.FREEZE]
    assert len(freeze_ev) == 0


def test_no_freeze_when_already_frozen():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    det.process("FIST", ctrl, 0.5, 0.5)  # first freeze

    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    events = det.process("FIST", ctrl, 0.5, 0.5)  # still frozen

    freeze_ev = [e for e in events if e.event_type == EventType.FREEZE]
    assert len(freeze_ev) == 0


def test_no_resume_when_not_previously_frozen():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    events = det.process("PINCH", ctrl, 0.5, 0.5)

    resume_ev = [e for e in events if e.event_type == EventType.RESUME]
    assert len(resume_ev) == 0


def test_multiple_freeze_resume_cycles():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    # Cycle 1: freeze → resume
    ctrl.process_frame("FIST", hand_x=0.5, hand_y=0.5)
    det.process("FIST", ctrl, 0.5, 0.5)
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    # Cycle 2: freeze → resume
    ctrl.process_frame("RELAXED", hand_x=0.5, hand_y=0.5)
    det.process("RELAXED", ctrl, 0.5, 0.5)

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    events = det.process("PINCH", ctrl, 0.5, 0.5)

    resume_ev = [e for e in events if e.event_type == EventType.RESUME]
    assert len(resume_ev) == 1


# ─────────────────────────────────────────────
# EventDetector: frame counting
# ─────────────────────────────────────────────

def test_frame_counter_advances():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    assert det.frame == 0

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    assert det.frame == 1

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    assert det.frame == 2


def test_events_have_correct_timestamps():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    grab_events = det.process("PINCH", ctrl, 0.5, 0.5)
    assert grab_events[0].timestamp == 1


# ─────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────

def test_no_hand_grab_event():
    """NO_HAND should not produce a GRAB event."""
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("NO_HAND")
    events = det.process("NO_HAND", ctrl)

    grab_ev = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_ev) == 0


def test_no_hand_after_grab_emits_release():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)

    ctrl.process_frame("NO_HAND")
    events = det.process("NO_HAND", ctrl)

    release_ev = [e for e in events if e.event_type == EventType.RELEASE]
    assert len(release_ev) == 1


def test_events_empty_when_nothing_happens():
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("UNKNOWN", hand_x=0.5, hand_y=0.5)
    events = det.process("UNKNOWN", ctrl, 0.5, 0.5)
    assert len(events) == 0


def test_grab_immediately_after_release():
    det = EventDetector(click_window=12)
    ctrl = SpatialInteractionController()

    # Click
    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    det.process("PINCH", ctrl, 0.5, 0.5)
    ctrl.process_frame("OPEN_PALM", hand_x=0.5, hand_y=0.5)
    det.process("OPEN_PALM", ctrl, 0.5, 0.5)

    # Immediately grab again
    ctrl.process_frame("PINCH", hand_x=0.6, hand_y=0.6)
    events = det.process("PINCH", ctrl, 0.6, 0.6)

    grab_ev = [e for e in events if e.event_type == EventType.GRAB]
    assert len(grab_ev) == 1


def test_detector_does_not_modify_controller():
    """EventDetector must be purely observational."""
    det = EventDetector()
    ctrl = SpatialInteractionController()

    ctrl.process_frame("PINCH", hand_x=0.5, hand_y=0.5)
    state_before = ctrl.state
    sphere_before = (ctrl.sphere_position.x, ctrl.sphere_position.y)

    det.process("PINCH", ctrl, 0.5, 0.5)

    assert ctrl.state == state_before
    assert (ctrl.sphere_position.x, ctrl.sphere_position.y) == sphere_before
