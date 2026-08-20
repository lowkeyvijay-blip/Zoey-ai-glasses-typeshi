"""Shared test fixtures for Zoey Spatial."""

from __future__ import annotations

import pytest

from backend.gestures.gesture_engine import detect_gesture
from backend.gestures.gesture_smoother import GestureSmoother
from backend.interaction.controller import SpatialInteractionController


class Landmark:
    """Mock MediaPipe landmark for testing."""

    def __init__(self, x: float, y: float, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z


@pytest.fixture
def blank_hand():
    """Return a blank hand with all 21 landmarks at (0.5, 0.5)."""
    return [Landmark(0.5, 0.5) for _ in range(21)]


@pytest.fixture
def pinch_hand():
    """Return a hand with thumb+index pinched."""
    hand = [Landmark(0.5, 0.5) for _ in range(21)]
    hand[4] = Landmark(0.50, 0.50)
    hand[8] = Landmark(0.52, 0.50)
    return hand


@pytest.fixture
def open_palm_hand():
    """Return a hand with all fingers extended."""
    hand = [Landmark(0.5, 0.5) for _ in range(21)]
    hand[8] = Landmark(0.50, 0.30)
    hand[6] = Landmark(0.50, 0.50)
    hand[12] = Landmark(0.60, 0.30)
    hand[10] = Landmark(0.60, 0.50)
    hand[16] = Landmark(0.65, 0.30)
    hand[14] = Landmark(0.65, 0.50)
    hand[20] = Landmark(0.70, 0.30)
    hand[18] = Landmark(0.70, 0.50)
    return hand


@pytest.fixture
def point_hand():
    """Return a hand with only index finger extended."""
    hand = [Landmark(0.5, 0.5) for _ in range(21)]
    hand[8] = Landmark(0.50, 0.30)
    hand[6] = Landmark(0.50, 0.50)
    hand[12] = Landmark(0.60, 0.60)
    hand[10] = Landmark(0.60, 0.50)
    hand[16] = Landmark(0.65, 0.60)
    hand[14] = Landmark(0.65, 0.50)
    hand[20] = Landmark(0.70, 0.60)
    hand[18] = Landmark(0.70, 0.50)
    return hand


@pytest.fixture
def fist_hand():
    """Return a hand with no fingers extended."""
    return [Landmark(0.5, 0.6) for _ in range(21)]


@pytest.fixture
def controller():
    """Return a fresh SpatialInteractionController."""
    return SpatialInteractionController()


@pytest.fixture
def smoother():
    """Return a fresh GestureSmoother."""
    return GestureSmoother(window_size=5)
