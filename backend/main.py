import asyncio
import json

import cv2
import mediapipe as mp

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.gestures.gesture_engine import detect_gesture
from backend.gestures.gesture_smoother import GestureSmoother


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


MODEL_PATH = "models/hand_landmarker.task"


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


detector = vision.HandLandmarker.create_from_options(
    options
)


camera = cv2.VideoCapture(0)

smoother = GestureSmoother(
    window_size=5
)


@app.get("/")
def root():
    return {
        "status": "Zoey Spatial backend running"
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    timestamp = 0

    try:

        while True:

            success, frame = camera.read()

            if not success:
                await asyncio.sleep(0.01)
                continue


            frame = cv2.flip(
                frame,
                1
            )


            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )


            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )


            result = detector.detect_for_video(
                image,
                timestamp
            )

            timestamp += 33


            if result.hand_landmarks:

                hand = result.hand_landmarks[0]

                raw_gesture = detect_gesture(
                    hand
                )

                gesture = smoother.update(
                    raw_gesture
                )


                # Index fingertip
                index_tip = hand[8]


                payload = {
                    "x": index_tip.x,
                    "y": index_tip.y,
                    "gesture": gesture
                }


                await websocket.send_text(
                    json.dumps(payload)
                )

            else:

                smoother.reset()

                await websocket.send_text(
                    json.dumps({
                        "gesture": "NO_HAND"
                    })
                )


            await asyncio.sleep(0.001)


    except Exception as e:

        print(
            "WebSocket closed:",
            e
        )