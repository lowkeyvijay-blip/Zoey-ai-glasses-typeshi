from collections import deque


class GestureSmoother:
    """
    Stabilizes noisy gesture predictions.

    A gesture must appear consistently across
    several frames before becoming the stable gesture.
    """

    def __init__(self, window_size=5):

        self.window_size = window_size

        self.history = deque(
            maxlen=window_size
        )

        self.current = "UNKNOWN"


    def update(self, gesture):

        self.history.append(gesture)

        # Not enough history yet
        if len(self.history) < self.window_size:
            return self.current

        # Count occurrences
        counts = {}

        for item in self.history:
            counts[item] = counts.get(item, 0) + 1

        # Most common gesture
        stable_gesture = max(
            counts,
            key=counts.get
        )

        # Require majority
        if counts[stable_gesture] >= 3:
            self.current = stable_gesture

        return self.current


    def reset(self):

        self.history.clear()

        self.current = "UNKNOWN"