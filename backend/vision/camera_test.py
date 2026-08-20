import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.gestures.gesture_engine import detect_gesture
from backend.gestures.gesture_smoother import GestureSmoother


MODEL_PATH = "models/hand_landmarker.task"


# ─────────────────────────────────────────────
# MediaPipe
# ─────────────────────────────────────────────

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

detector = vision.HandLandmarker.create_from_options(
    options
)


# ─────────────────────────────────────────────
# Camera
# ─────────────────────────────────────────────

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Could not open camera")


frame_timestamp_ms = 0


# One smoother per hand
smoothers = [
    GestureSmoother(window_size=5),
    GestureSmoother(window_size=5),
]


# ─────────────────────────────────────────────
# Main Loop
# ─────────────────────────────────────────────

while True:

    success, frame = cap.read()

    if not success:
        continue

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = detector.detect_for_video(
        mp_image,
        frame_timestamp_ms
    )

    frame_timestamp_ms += 33


    # ─────────────────────────────────────────
    # Hands
    # ─────────────────────────────────────────

    if result.hand_landmarks:

        for hand_index, hand in enumerate(
            result.hand_landmarks
        ):

            # Raw gesture
            raw_gesture = detect_gesture(hand)

            # Stabilized gesture
            gesture = smoothers[
                hand_index
            ].update(raw_gesture)


            h, w, _ = frame.shape


            # ─────────────────────────────────────
            # Landmarks
            # ─────────────────────────────────────

            for landmark in hand:

                x = int(landmark.x * w)
                y = int(landmark.y * h)

                cv2.circle(
                    frame,
                    (x, y),
                    5,
                    (0, 255, 0),
                    -1
                )


            # ─────────────────────────────────────
            # Connections
            # ─────────────────────────────────────

            connections = [
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 4),

                (0, 5),
                (5, 6),
                (6, 7),
                (7, 8),

                (0, 9),
                (9, 10),
                (10, 11),
                (11, 12),

                (0, 13),
                (13, 14),
                (14, 15),
                (15, 16),

                (0, 17),
                (17, 18),
                (18, 19),
                (19, 20),

                (5, 9),
                (9, 13),
                (13, 17),
            ]


            for start, end in connections:

                x1 = int(hand[start].x * w)
                y1 = int(hand[start].y * h)

                x2 = int(hand[end].x * w)
                y2 = int(hand[end].y * h)

                cv2.line(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )


            # ─────────────────────────────────────
            # Gesture UI
            # ─────────────────────────────────────

            label_y = 120 + (
                hand_index * 50
            )

            cv2.putText(
                frame,
                f"Hand {hand_index + 1}: {gesture}",
                (20, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )


    else:

        # Reset both smoothers when no hands
        for smoother in smoothers:
            smoother.reset()


    # ─────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────

    cv2.putText(
        frame,
        "ZOEY SPATIAL V1.2",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "Gesture Stabilization Active",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Q = Quit",
        (20, frame.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "Zoey Spatial V1.2",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────

cap.release()

detector.close()

cv2.destroyAllWindows()