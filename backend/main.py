"""Zoey Spatial backend server.

FastAPI application with WebSocket endpoint for real-time
hand tracking and spatial interaction.

V1.5: Uses CameraManager, per-session InteractionController,
      EventDetector, and sends authoritative state + events
      to frontend.
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
from backend.interaction.controller import SpatialInteractionController
from backend.interaction.event_detector import EventDetector
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
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    return vision.HandLandmarker.create_from_options(options)


detector = _create_detector()

camera = CameraManager(camera_index=0)


@app.get("/")
def root():
    return {"status": "Zoey Spatial backend running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    smoother = GestureSmoother(window_size=5)
    controller = SpatialInteractionController()
    event_detector = EventDetector(
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

            if result.hand_landmarks:
                hand = result.hand_landmarks[0]

                raw_gesture = detect_gesture(hand)
                gesture = smoother.update(raw_gesture)

                index_tip = hand[8]

                interaction = controller.process_frame(
                    gesture=gesture,
                    hand_x=index_tip.x,
                    hand_y=index_tip.y,
                )

                events = event_detector.process(
                    gesture=gesture,
                    controller=controller,
                    hand_x=index_tip.x,
                    hand_y=index_tip.y,
                )

                payload = {
                    "hand_x": index_tip.x,
                    "hand_y": index_tip.y,
                    "gesture": gesture,
                    "sphere_x": interaction.sphere_position.x,
                    "sphere_y": interaction.sphere_position.y,
                    "interaction_state": interaction.interaction_state,
                    "events": [
                        {
                            "type": ev.event_type.value,
                            "timestamp": ev.timestamp,
                        }
                        for ev in events
                    ],
                }

            else:
                smoother.reset()

                interaction = controller.process_frame(
                    gesture="NO_HAND",
                )

                events = event_detector.process(
                    gesture="NO_HAND",
                    controller=controller,
                )

                payload = {
                    "gesture": "NO_HAND",
                    "sphere_x": interaction.sphere_position.x,
                    "sphere_y": interaction.sphere_position.y,
                    "interaction_state": interaction.interaction_state,
                    "events": [
                        {
                            "type": ev.event_type.value,
                            "timestamp": ev.timestamp,
                        }
                        for ev in events
                    ],
                }

            await websocket.send_text(json.dumps(payload))

            await asyncio.sleep(0.001)

    except Exception as e:
        logger.info("WebSocket closed: %s", e)
