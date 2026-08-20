"""Frame-based debouncer for interaction timing.

Used for click detection (quick grab+release) and
double-click detection (two rapid clicks).

Frame-based because the controller processes discrete frames
rather than wall-clock time.
"""

from __future__ import annotations


class Debouncer:
    """Tracks whether an event occurred within a frame window.

    Usage:
        debouncer = Debouncer(max_frames=10)
        debouncer.start()          # begin tracking
        for _ in range(5):
            debouncer.tick()       # advance one frame
        debouncer.is_within_window()  # True (5 <= 10)
    """

    def __init__(self, max_frames: int = 10) -> None:
        self._max_frames = max_frames
        self._active = False
        self._elapsed = 0

    @property
    def max_frames(self) -> int:
        return self._max_frames

    @property
    def elapsed(self) -> int:
        return self._elapsed

    def start(self) -> None:
        """Begin tracking from frame 0."""
        self._active = True
        self._elapsed = 0

    def tick(self) -> None:
        """Advance one frame while active."""
        if self._active:
            self._elapsed += 1

    def is_within_window(self) -> bool:
        """True if started and elapsed frames <= max_frames."""
        return self._active and self._elapsed <= self._max_frames

    def is_active(self) -> bool:
        return self._active

    def reset(self) -> None:
        """Clear all state."""
        self._active = False
        self._elapsed = 0
