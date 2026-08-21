"""Zoey Spatial backend server.

FastAPI application with WebSocket endpoint for real-time
hand tracking and spatial interaction.

V1.7: Uses CameraManager, per-session TwoHandController,
      TwoHandEventDetector, num_hands=2, DepthSmoother,
      and sends authoritative state + events to frontend.
      Maps MediaPipe z to world Z via DEPTH_SCALE.
"""

import asyncio
import json
import logging

import cv2
import mediapipe as mp

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.gestures.gesture_engine import detect_gesture
from backend.gestures.gesture_smoother import GestureSmoother
from backend.gestures.depth_smoother import DepthSmoother
from backend.interaction.controller import TwoHandController
from backend.interaction.event_detector import TwoHandEventDetector
from backend.vision.camera_manager import CameraManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zoey Spatial")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = "models/hand_landmarker.task"


def _create_detector() -> vision.HandLandmarker:
    base_options = python.BaseOptions(
        model_asset_path=MODEL_PATH
    )

    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    return vision.HandLandmarker.create_from_options(options)


detector = _create_detector()

camera = CameraManager(camera_index=0)

DEPTH_SCALE = 20.0


@app.get("/")
def root():
    return {"status": "Zoey Spatial backend running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    left_smoother = GestureSmoother(window_size=5)
    right_smoother = GestureSmoother(window_size=5)
    left_depth = DepthSmoother(alpha=0.3)
    right_depth = DepthSmoother(alpha=0.3)
    controller = TwoHandController()
    event_detector = TwoHandEventDetector(
        click_window=12,
        double_click_window=40,
    )
    timestamp = 0

    logger.info("WebSocket client connected")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                await asyncio.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb,
            )

            result = detector.detect_for_video(
                image,
                timestamp,
            )

            timestamp += 33

            left_gesture = "NO_HAND"
            left_x = None
            left_y = None
            left_z = None
            right_gesture = "NO_HAND"
            right_x = None
            right_y = None
            right_z = None

            if result.hand_landmarks and result.handedness:
                for i, hand_landmarks in enumerate(
                    result.hand_landmarks
                ):
                    handedness = result.handedness[i]
                    label = handedness[0].category_name

                    raw_gesture = detect_gesture(hand_landmarks)
                    index_tip = hand_landmarks[8]

                    if label == "Left":
                        left_gesture = left_smoother.update(
                            raw_gesture
                        )
                        left_x = index_tip.x
                        left_y = index_tip.y
                        left_z = left_depth.update(
                            index_tip.z
                        ) * DEPTH_SCALE
                    else:
                        right_gesture = right_smoother.update(
                            raw_gesture
                        )
                        right_x = index_tip.x
                        right_y = index_tip.y
                        right_z = right_depth.update(
                            index_tip.z
                        ) * DEPTH_SCALE

                # Reset smoothers for hands not detected this frame
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

            interaction = controller.process_frame(
                left_gesture=left_gesture,
                left_x=left_x,
                left_y=left_y,
                left_z=left_z,
                right_gesture=right_gesture,
                right_x=right_x,
                right_y=right_y,
                right_z=right_z,
            )

            events = event_detector.process(
                result=interaction,
                left_gesture=left_gesture,
                right_gesture=right_gesture,
            )

            payload = {
                "sphere_x": interaction.sphere_position.x,
                "sphere_y": interaction.sphere_position.y,
                "sphere_z": interaction.sphere_position.z,
                "sphere_scale": interaction.sphere_position.scale,
                "sphere_rotation": interaction.sphere_position.rotation,
                "interaction_state": interaction.interaction_state,
                "left_state": interaction.left_state.value,
                "right_state": interaction.right_state.value,
                "left_hand": (
                    {
                        "x": interaction.left_hand.x,
                        "y": interaction.left_hand.y,
                        "z": interaction.left_hand.z,
                    }
                    if interaction.left_hand
                    else None
                ),
                "right_hand": (
                    {
                        "x": interaction.right_hand.x,
                        "y": interaction.right_hand.y,
                        "z": interaction.right_hand.z,
                    }
                    if interaction.right_hand
                    else None
                ),
                "events": [
                    {
                        "type": ev.event_type.value,
                        "timestamp": ev.timestamp,
                        "hand_label": ev.hand_label,
                    }
                    for ev in events
                ],
            }

            await websocket.send_text(json.dumps(payload))

            await asyncio.sleep(0.001)

    except Exception as e:
        logger.info("WebSocket closed: %s", e)
