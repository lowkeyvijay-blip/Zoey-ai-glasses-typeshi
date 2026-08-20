import math


def distance(a, b):
    """3D distance between two MediaPipe landmarks."""
    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2 +
        (a.z - b.z) ** 2
    )


def finger_extended(hand, tip, pip):
    """
    Basic finger-extension test.

    MediaPipe coordinates have Y increasing downward,
    so a smaller Y means the fingertip is higher.
    """
    return hand[tip].y < hand[pip].y


def detect_gesture(hand):
    """
    Detect the current hand pose.

    Returns:
        PINCH
        POINT
        OPEN_PALM
        FIST
        RELAXED
        UNKNOWN
    """

    # ─────────────────────────────────────────
    # PINCH
    # ─────────────────────────────────────────

    thumb_tip = hand[4]
    index_tip = hand[8]

    pinch_distance = distance(thumb_tip, index_tip)

    if pinch_distance < 0.07:
        return "PINCH"


    # ─────────────────────────────────────────
    # Finger states
    # ─────────────────────────────────────────

    index = finger_extended(hand, 8, 6)
    middle = finger_extended(hand, 12, 10)
    ring = finger_extended(hand, 16, 14)
    pinky = finger_extended(hand, 20, 18)


    extended_count = sum([
        index,
        middle,
        ring,
        pinky
    ])


    # ─────────────────────────────────────────
    # OPEN PALM
    # ─────────────────────────────────────────

    if extended_count == 4:
        return "OPEN_PALM"


    # ─────────────────────────────────────────
    # POINT
    # ─────────────────────────────────────────

    if (
        index
        and not middle
        and not ring
        and not pinky
    ):
        return "POINT"


    # ─────────────────────────────────────────
    # FIST
    # ─────────────────────────────────────────

    if extended_count == 0:
        return "FIST"


    # ─────────────────────────────────────────
    # RELAXED / PARTIAL HAND
    # ─────────────────────────────────────────

    if extended_count in (1, 2, 3):
        return "RELAXED"


    return "UNKNOWN"