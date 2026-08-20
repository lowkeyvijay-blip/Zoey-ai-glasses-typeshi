"""Shared camera manager.

Provides a single CameraManager that owns the physical camera.
All WebSocket sessions share this one instance.

The camera is opened lazily on first read and reused for
subsequent reads. If the camera is unavailable, reads return
(success=False) without crashing.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class CameraManager:
    """Thread-safe camera manager.

    Uses a simple open-once, reuse pattern.
    Designed for single-process FastAPI server
    where all WebSocket endpoints run on the
    same event loop.
    """

    def __init__(self, camera_index: int = 0) -> None:
        self._camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._opened = False

    def _ensure_opened(self) -> bool:
        if self._opened and self._cap is not None:
            return True

        try:
            self._cap = cv2.VideoCapture(self._camera_index)

            if not self._cap.isOpened():
                logger.warning(
                    "Camera %d could not be opened",
                    self._camera_index,
                )
                self._cap = None
                self._opened = False
                return False

            self._opened = True
            logger.info(
                "Camera %d opened successfully",
                self._camera_index,
            )
            return True

        except Exception:
            logger.exception("Failed to open camera %d", self._camera_index)
            self._cap = None
            self._opened = False
            return False

    def read(self) -> Tuple[bool, Optional[object]]:
        """Read a frame from the camera.

        Returns:
            (success, frame) tuple. If camera is unavailable
            or read fails, returns (False, None).
        """
        if not self._ensure_opened():
            return False, None

        assert self._cap is not None

        success, frame = self._cap.read()

        if not success:
            logger.warning("Camera read failed, attempting reopen")
            self._release()
            return False, None

        return True, frame

    def _release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
        self._cap = None
        self._opened = False

    def close(self) -> None:
        """Release camera resources."""
        self._release()
        logger.info("Camera released")
