"""Tests for the frame-based debouncer.

Covers:
  - Initial state
  - start / tick / reset lifecycle
  - is_within_window behavior
  - max_frames boundary
  - elapsed tracking
"""

from backend.interaction.debouncer import Debouncer


def test_initial_state():
    d = Debouncer(max_frames=10)
    assert not d.is_active()
    assert not d.is_within_window()
    assert d.elapsed == 0
    assert d.max_frames == 10


def test_start():
    d = Debouncer(max_frames=10)
    d.start()
    assert d.is_active()
    assert d.is_within_window()
    assert d.elapsed == 0


def test_tick_advances():
    d = Debouncer(max_frames=10)
    d.start()
    d.tick()
    assert d.elapsed == 1
    d.tick()
    assert d.elapsed == 2


def test_within_window():
    d = Debouncer(max_frames=5)
    d.start()
    for _ in range(5):
        d.tick()
    assert d.is_within_window()


def test_outside_window():
    d = Debouncer(max_frames=5)
    d.start()
    for _ in range(6):
        d.tick()
    assert not d.is_within_window()


def test_at_exact_boundary():
    d = Debouncer(max_frames=3)
    d.start()
    d.tick()
    d.tick()
    d.tick()
    assert d.is_within_window()  # elapsed=3 <= max=3


def test_one_past_boundary():
    d = Debouncer(max_frames=3)
    d.start()
    d.tick()
    d.tick()
    d.tick()
    d.tick()
    assert not d.is_within_window()  # elapsed=4 > max=3


def test_reset():
    d = Debouncer(max_frames=10)
    d.start()
    d.tick()
    d.tick()
    d.reset()
    assert not d.is_active()
    assert not d.is_within_window()
    assert d.elapsed == 0


def test_tick_when_not_active():
    d = Debouncer(max_frames=10)
    d.tick()
    d.tick()
    assert d.elapsed == 0
    assert not d.is_within_window()


def test_reuse_after_reset():
    d = Debouncer(max_frames=3)
    d.start()
    d.tick()
    d.tick()
    d.reset()
    d.start()
    d.tick()
    assert d.is_within_window()
    assert d.elapsed == 1


def test_single_frame_click():
    d = Debouncer(max_frames=1)
    d.start()
    d.tick()
    assert d.is_within_window()
    d.tick()
    assert not d.is_within_window()
