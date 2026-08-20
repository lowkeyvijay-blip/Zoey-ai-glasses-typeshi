from gesture_engine import detect_gesture


class Landmark:
    def __init__(self, x, y, z=0):
        self.x = x
        self.y = y
        self.z = z


def blank_hand():
    return [Landmark(0.5, 0.5) for _ in range(21)]


def test_pinch():
    hand = blank_hand()

    # Thumb + index very close
    hand[4] = Landmark(0.50, 0.50)
    hand[8] = Landmark(0.52, 0.50)

    assert detect_gesture(hand) == "PINCH"


def test_point():
    hand = blank_hand()

    # Index extended
    hand[8] = Landmark(0.50, 0.30)
    hand[6] = Landmark(0.50, 0.50)

    # Other fingers folded
    hand[12] = Landmark(0.60, 0.60)
    hand[10] = Landmark(0.60, 0.50)

    hand[16] = Landmark(0.65, 0.60)
    hand[14] = Landmark(0.65, 0.50)

    hand[20] = Landmark(0.70, 0.60)
    hand[18] = Landmark(0.70, 0.50)

    assert detect_gesture(hand) == "POINT"


def test_open_palm():
    hand = blank_hand()

    # All fingers extended
    hand[8] = Landmark(0.50, 0.30)
    hand[6] = Landmark(0.50, 0.50)

    hand[12] = Landmark(0.60, 0.30)
    hand[10] = Landmark(0.60, 0.50)

    hand[16] = Landmark(0.65, 0.30)
    hand[14] = Landmark(0.65, 0.50)

    hand[20] = Landmark(0.70, 0.30)
    hand[18] = Landmark(0.70, 0.50)

    assert detect_gesture(hand) == "OPEN_PALM"


if __name__ == "__main__":
    test_pinch()
    print("✓ PINCH")

    test_point()
    print("✓ POINT")

    test_open_palm()
    print("✓ OPEN_PALM")

    print("\nGesture engine tests passed.")