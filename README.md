# Zoey Spatial V1.3

Real-time hand tracking and spatial control system. A webcam detects hand gestures via MediaPipe, and the classified gesture + fingertip position are streamed over WebSocket to a Three.js frontend that drives a 3D sphere.

## Status

**V1.3** - Working prototype. Camera gesture detection, gesture stabilization, and 3D sphere tracking are functional.

## Technologies

- **Backend:** Python 3.11, FastAPI, MediaPipe, OpenCV
- **Frontend:** Three.js (via CDN), vanilla JavaScript, HTML/CSS
- **Communication:** WebSocket

## Capabilities

- Real-time hand landmark detection via webcam
- Gesture classification: PINCH, OPEN_PALM, POINT, FIST, RELAXED, UNKNOWN
- Gesture smoothing (sliding-window majority vote)
- Fingertip position tracking mapped to 3D sphere movement
- Standalone camera test with hand skeleton visualization

## Project Structure

```
Zoey-Spatial/
├── backend/
│   ├── main.py                  # FastAPI server, WebSocket endpoint, camera loop
│   ├── gestures/
│   │   ├── gesture_engine.py    # Gesture classification logic
│   │   ├── gesture_smoother.py  # Sliding-window gesture stabilizer
│   │   └── test_gesture.py      # Standalone gesture unit tests
│   └── vision/
│       └── camera_test.py       # Standalone camera + hand visualization test
├── frontend/
│   ├── index.html               # Page shell with HUD overlay
│   ├── app.js                   # Three.js scene + WebSocket client
│   └── style.css                # Fullscreen HUD styling
├── models/
│   └── hand_landmarker.task     # MediaPipe hand model (downloaded separately)
├── tests/                       # (empty)
├── requirements.txt
└── README.md
```

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/Zoey-Spatial.git
cd Zoey-Spatial
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## Model Setup

The project requires the MediaPipe `hand_landmarker.task` model file. It is **not** included in the repository.

1. Download from [MediaPipe hand landmarker models](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#model-cards)
2. Place the file at:

```
models/hand_landmarker.task
```

## Running

### Camera / Gesture Test (standalone)

```bash
python -m backend.vision.camera_test
```

Opens a window showing the webcam feed with hand landmarks drawn and gesture labels. Press **Q** to quit.

### Full Application (backend + frontend)

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open `frontend/index.html` in a browser.

## Gesture Controls

| Gesture | Description |
|---------|-------------|
| **PINCH** | Thumb and index finger close together |
| **OPEN_PALM** | All four fingers extended |
| **POINT** | Only index finger extended |
| **FIST** | No fingers extended |
| **RELAXED** | 1-3 fingers extended (partial hand) |
| **UNKNOWN** | Unrecognized or transitioning state |

## Development Roadmap

- Gesture-to-action mapping (grab, release, menu triggers)
- Multi-hand support in the WebSocket stream
- Visual gesture feedback on the frontend
- Persistent configuration via environment variables
- Improved gesture precision and new gesture types
