"""Zoey Spatial V2.0 backend server.

FastAPI application with WebSocket endpoint for real-time
hand tracking and spatial interaction.

V2.0: Session isolation, protocol handshake, lifecycle management,
      centralized config. main.py contains NO business logic —
      only vision capture and WebSocket plumbing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

import cv2
import mediapipe as mp

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.config.settings import get_settings
from backend.gestures.gesture_engine import detect_gesture
from backend.gestures.gesture_smoother import GestureSmoother
from backend.gestures.depth_smoother import DepthSmoother
from backend.pipeline import Pipeline
from backend.protocol.handler import ProtocolHandler
from backend.protocol.messages import MessageType
from backend.vision.camera_manager import CameraManager
from backend.lifecycle.manager import LifecycleManager

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zoey Spatial", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

lifecycle = LifecycleManager(settings)


def _create_detector() -> Optional[vision.HandLandmarker]:
    """Create MediaPipe hand landmarker. Returns None on failure."""
    try:
        base_options = python.BaseOptions(
            model_asset_path=settings.model_path
        )
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=settings.num_hands,
            min_hand_detection_confidence=settings.min_detection_confidence,
            min_hand_presence_confidence=settings.min_presence_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
        )
        detector = vision.HandLandmarker.create_from_options(options)
        lifecycle.register_component("mediapipe", "ready")
        return detector
    except Exception:
        logger.exception("Failed to initialize MediaPipe model")
        lifecycle.register_component("mediapipe", "unavailable")
        return None


detector: Optional[vision.HandLandmarker] = _create_detector()
camera = CameraManager(camera_index=settings.camera_index)
lifecycle.register_component("camera", "registered")


@app.get("/")
def root():
    return {"status": "Zoey Spatial V2.0 running", "version": "2.0"}


@app.get("/health")
def health():
    return lifecycle.health()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())[:8]
    protocol = ProtocolHandler(session_id=session_id)

    left_smoother = GestureSmoother(window_size=settings.gesture_smoother_window)
    right_smoother = GestureSmoother(window_size=settings.gesture_smoother_window)
    left_depth = DepthSmoother(alpha=settings.depth_smoothing_alpha)
    right_depth = DepthSmoother(alpha=settings.depth_smoothing_alpha)
    pipeline = Pipeline()

    lifecycle.register_component(f"session_{session_id}", "active")
    logger.info("Session %s connected", session_id)

    try:
        while True:
            try:
                raw_msg = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.01,
                )

                msg = protocol.parse_message(raw_msg)

                if msg is not None and msg.type == MessageType.HANDSHAKE:
                    ack = protocol.handle_handshake(msg)
                    await websocket.send_text(json.dumps(ack.to_dict()))
                    continue

                if msg is not None and msg.type == MessageType.PING:
                    pong = protocol.handle_ping()
                    await websocket.send_text(json.dumps(pong.to_dict()))
                    continue

                if msg is not None and msg.type == MessageType.UNKNOWN:
                    err = protocol.create_error("Unknown message type")
                    await websocket.send_text(json.dumps(err.to_dict()))
                    continue

            except asyncio.TimeoutError:
                pass

            if detector is None:
                await asyncio.sleep(0.01)
                continue

            success, frame = camera.read()

            if not success or frame is None:
                await asyncio.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            timestamp = int(time.monotonic() * 1000)
            result = detector.detect_for_video(image, timestamp)

            left_gesture = "NO_HAND"
            left_x = None
            left_y = None
            left_z = None
            right_gesture = "NO_HAND"
            right_x = None
            right_y = None
            right_z = None

            if result.hand_landmarks and result.handedness:
                for i, hand_landmarks in enumerate(result.hand_landmarks):
                    handedness = result.handedness[i]
                    label = handedness[0].category_name

                    raw_gesture = detect_gesture(hand_landmarks)
                    index_tip = hand_landmarks[8]

                    if label == "Left":
                        left_gesture = left_smoother.update(raw_gesture)
                        left_x = index_tip.x
                        left_y = index_tip.y
                        left_z = left_depth.update(index_tip.z) * settings.depth_scale
                    else:
                        right_gesture = right_smoother.update(raw_gesture)
                        right_x = index_tip.x
                        right_y = index_tip.y
                        right_z = right_depth.update(index_tip.z) * settings.depth_scale

                if left_x is None:
                    left_smoother.reset()
                    left_depth.reset()
                if right_x is None:
                    right_smoother.reset()
                    right_depth.reset()

            else:
                left_smoother.reset()
                right_smoother.reset()
                left_depth.reset()
                right_depth.reset()

            frame_result = pipeline.process_frame(
                left_gesture=left_gesture,
                left_x=left_x, left_y=left_y, left_z=left_z,
                right_gesture=right_gesture,
                right_x=right_x, right_y=right_y, right_z=right_z,
                timestamp=timestamp,
            )

            await websocket.send_text(frame_result.to_json())

            await asyncio.sleep(0.001)

    except WebSocketDisconnect:
        logger.info("Session %s disconnected", session_id)
    except Exception:
        logger.exception("Session %s error", session_id)
    finally:
        lifecycle.update_component(f"session_{session_id}", "closed")
        logger.info("Session %s cleaned up", session_id)
