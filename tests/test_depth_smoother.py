"""Tests for DepthSmoother — V1.7 depth smoothing.

EMA-based exponential moving average for noisy MediaPipe z values.
"""

import pytest

from backend.gestures.depth_smoother import DepthSmoother


class TestDepthSmootherBasic:
    """Basic DepthSmoother behavior."""

    def test_first_sample_returned_directly(self):
        s = DepthSmoother(alpha=0.3)
        assert s.update(-0.05) == -0.05

    def test_second_sample_smoothed(self):
        s = DepthSmoother(alpha=0.3)
        s.update(0.0)
        result = s.update(0.1)
        expected = 0.0 + 0.3 * (0.1 - 0.0)
        assert abs(result - expected) < 1e-9

    def test_third_sample_smoothed(self):
        s = DepthSmoother(alpha=0.3)
        v1 = s.update(0.0)
        v2 = s.update(0.1)
        v3 = s.update(0.2)
        expected = v2 + 0.3 * (0.2 - v2)
        assert abs(v3 - expected) < 1e-9


class TestDepthSmootherReset:
    """Reset behavior."""

    def test_reset_clears_state(self):
        s = DepthSmoother(alpha=0.3)
        s.update(0.0)
        s.update(0.1)
        s.update(0.2)
        s.reset()
        assert s._value is None

    def test_first_sample_after_reset(self):
        s = DepthSmoother(alpha=0.3)
        s.update(0.0)
        s.update(0.1)
        s.reset()
        result = s.update(0.5)
        assert result == 0.5


class TestDepthSmootherAlpha:
    """Alpha parameter effects."""

    def test_alpha_1_is_no_smoothing(self):
        s = DepthSmoother(alpha=1.0)
        s.update(0.0)
        assert s.update(0.5) == 0.5
        assert s.update(0.8) == 0.8

    def test_alpha_near_zero_heavily_smooths(self):
        s = DepthSmoother(alpha=0.01)
        s.update(0.0)
        result = s.update(1.0)
        assert abs(result - 0.01) < 1e-9

    def test_alpha_rejects_zero(self):
        with pytest.raises(ValueError):
            DepthSmoother(alpha=0.0)


class TestDepthSmootherNegativeValues:
    """Negative z values (closer to camera) are common."""

    def test_negative_z_smoothed(self):
        s = DepthSmoother(alpha=0.3)
        s.update(-0.05)
        result = s.update(-0.08)
        expected = -0.05 + 0.3 * (-0.08 - (-0.05))
        assert abs(result - expected) < 1e-9

    def test_sign_preserved(self):
        s = DepthSmoother(alpha=0.3)
        s.update(0.0)
        result = s.update(-0.1)
        assert result < 0.0

    def test_positive_preserved(self):
        s = DepthSmoother(alpha=0.3)
        s.update(0.0)
        result = s.update(0.1)
        assert result > 0.0
