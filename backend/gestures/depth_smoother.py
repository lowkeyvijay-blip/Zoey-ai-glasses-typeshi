"""EMA-based depth smoother for MediaPipe z-coordinates.

MediaPipe z is noisier than x/y because it is estimated from
a single RGB image without stereo depth.  This module provides
an exponential moving average (EMA) filter that can be tuned
independently from the gesture smoother.

Coordinate documentation (V1.7):
    MediaPipe z is the landmark's depth relative to the wrist.
    Negative z = closer to camera.  Positive z = farther.
    Scale is roughly the same as x (image width), so typical
    hand-distance range is about [-0.1, 0.1].

    The backend applies DEPTH_SCALE (default 20.0) to convert
    this into world-space Z:  world_z = smoothed_z * DEPTH_SCALE.
    The resulting range is approximately [-2.0, +2.0], which
    maps naturally onto the Three.js scene where the camera
    sits at z = 5 looking toward -Z.
"""

from __future__ import annotations

from typing import Optional


class DepthSmoother:
    """Exponential moving average filter for depth values.

    Args:
        alpha: Smoothing factor in (0, 1].
               Lower = smoother but more latent.
               Higher = more responsive but noisier.
               0.3 is a good starting point for MediaPipe z.
    """

    def __init__(self, alpha: float = 0.3) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(
                f"alpha must be in (0, 1], got {alpha}"
            )
        self._alpha = alpha
        self._value: Optional[float] = None

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def current(self) -> Optional[float]:
        """Most recent smoothed value, or None if not yet seeded."""
        return self._value

    def update(self, raw_z: float) -> float:
        """Feed a raw z value and return the smoothed result.

        On the first call the raw value is used directly (no
        smoothing artefact from a cold start).
        """
        if self._value is None:
            self._value = raw_z
        else:
            self._value = (
                self._alpha * raw_z
                + (1.0 - self._alpha) * self._value
            )
        return self._value

    def reset(self) -> None:
        """Clear state — call when the tracked hand disappears."""
        self._value = None
