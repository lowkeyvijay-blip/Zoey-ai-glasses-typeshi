"""V2.0 Gesture engine.

Classifies hand gestures from MediaPipe landmarks.
Preserves all existing gesture behavior.

Gestures: PINCH, POINT, OPEN_PALM, FIST, RELAXED, UNKNOWN
"""

from __future__ import annotations

import math
from typing import List, Optional

try:
    from mediapipe.framework.formats.landmark_pb2 import (
        NormalizedLandmarkList,
    )
except ImportError:
    NormalizedLandmarkList = None


def distance(a: object, b: object) -> float:
    """3D distance between two MediaPipe landmarks."""
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


def finger_extended(hand: object, tip: int, pip: int) -> bool:
    """Basic finger-extension test.

    MediaPipe coordinates have Y increasing downward,
    so a smaller Y means the fingertip is higher.
    """
    try:
        return hand[tip].y < hand[pip].y
    except (IndexError, AttributeError, TypeError):
        return False


def detect_gesture(hand: object) -> str:
    """Detect the current hand pose.

    Args:
        hand: A list of 21 MediaPipe hand landmarks.

    Returns:
        One of: PINCH, POINT, OPEN_PALM, FIST, RELAXED, UNKNOWN
    """
    if hand is None or len(hand) < 21:
        return "UNKNOWN"

    try:
        thumb_tip = hand[4]
        index_tip = hand[8]
    except (IndexError, AttributeError):
        return "UNKNOWN"

    pinch_distance = distance(thumb_tip, index_tip)

    if pinch_distance < 0.07:
        return "PINCH"

    index = finger_extended(hand, 8, 6)
    middle = finger_extended(hand, 12, 10)
    ring = finger_extended(hand, 16, 14)
    pinky = finger_extended(hand, 20, 18)

    extended_count = sum([index, middle, ring, pinky])

    if extended_count == 4:
        return "OPEN_PALM"

    if index and not middle and not ring and not pinky:
        return "POINT"

    if extended_count == 0:
        return "FIST"

    if extended_count in (1, 2, 3):
        return "RELAXED"

    return "UNKNOWN"
