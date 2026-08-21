# Zoey Spatial V2.0

Real-time hand tracking and spatial interaction system. A webcam detects hand gestures via MediaPipe, and the pipeline processes them through gesture classification, 3D depth mapping, intent resolution, and scene mutation — all streamed to a Three.js frontend over WebSocket.

## Status

**V2.0** — Final target. Session-isolated backend, typed protocol, lifecycle management, rule-based assistant, full test suite (429 tests).

## Technologies

- **Backend:** Python 3.11, FastAPI, MediaPipe, OpenCV
- **Frontend:** Three.js (via CDN), vanilla JavaScript, HTML/CSS
- **Communication:** Typed WebSocket protocol with handshake, ping/pong, version negotiation

## Capabilities

- Real-time hand landmark detection via webcam
- Gesture classification: PINCH, OPEN_PALM, POINT, FIST, RELAXED, UNKNOWN
- Gesture smoothing (sliding-window majority vote)
- 3D depth tracking via MediaPipe z-axis with EMA smoothing
- Object interaction: hover, select, grab, release, click, double-click
- Two-hand scaling and rotation of objects
- Intent resolution engine (event → intent → action)
- Rule-based spatial assistant (no LLM required)
- Typed protocol with handshake, version negotiation, error handling
- Per-session isolation — concurrent clients don't corrupt each other
- Lifecycle management with health endpoint

## Project Structure

```
Zoey-Spatial/
├── backend/
│   ├── main.py                      # FastAPI app, WebSocket endpoint (thin)
│   ├── pipeline.py                  # Central orchestrator
│   ├── config/
│   │   └── settings.py              # Centralized config with env overrides
│   ├── errors/
│   │   └── exceptions.py            # Exception hierarchy
│   ├── tracking/
│   │   └── hand_state.py            # Per-hand tracking state
│   ├── assistant/
│   │   ├── interface.py             # AssistantInterface ABC
│   │   └── rule_engine.py           # RuleBasedAssistant (no LLM)
│   ├── protocol/
│   │   ├── messages.py              # Typed/versioned protocol messages
│   │   └── handler.py               # Protocol handshake, version negotiation
│   ├── lifecycle/
│   │   └── manager.py               # Startup/shutdown hooks, health
│   ├── gestures/
│   │   ├── gesture_engine.py        # Gesture classification
│   │   ├── gesture_smoother.py      # Sliding-window stabilizer
│   │   └── depth_smoother.py        # EMA depth smoothing
│   ├── interaction/
│   │   ├── controller.py            # TwoHandController (grab, scale, rotate)
│   │   ├── event_detector.py        # TwoHandEventDetector (click, double-click)
│   │   └── events.py                # InteractionEvent types
│   ├── intent/
│   │   ├── types.py                 # IntentType enum, Intent dataclass
│   │   ├── engine.py                # IntentEngine (events → intents)
│   │   └── llm_interface.py         # LLMInterface ABC + NullLLM
│   ├── action/
│   │   ├── types.py                 # ActionType enum, Action dataclass
│   │   └── engine.py                # ActionEngine (intents → scene mutations)
│   ├── scene/
│   │   ├── scene.py                 # Scene registry (authoritative object store)
│   │   ├── spatial_object.py        # SpatialObject, ObjectType, ObjectState
│   │   └── object_interaction.py    # Per-hand interaction state machine
│   └── vision/
│       └── camera_manager.py        # Camera manager with lazy init
├── frontend/
│   ├── index.html                   # Page shell with HUD overlay
│   ├── app.js                       # Three.js scene + WebSocket client
│   └── style.css                    # Fullscreen HUD styling
├── models/
│   └── hand_landmarker.task         # MediaPipe hand model (not in repo)
├── tests/                           # 429 tests, zero external dependencies
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

### Full Application (backend + frontend)

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open `frontend/index.html` in a browser.

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Running Tests

```bash
pytest -q
```

All 429 tests run without webcam, GUI, server, frontend, network, or LLM.

## Configuration

All runtime constants are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZOEY_MODEL_PATH` | `models/hand_landmarker.task` | MediaPipe model path |
| `ZOEY_CAMERA_INDEX` | `0` | Camera device index |
| `ZOEY_NUM_HANDS` | `2` | Max simultaneous hands |
| `ZOEY_DEPTH_SCALE` | `20.0` | Depth z-axis multiplier |
| `ZOEY_DEPTH_SMOOTHING_ALPHA` | `0.3` | EMA smoothing factor |
| `ZOEY_GESTURE_SMOOTHER_WINDOW` | `5` | Sliding-window size |
| `ZOEY_LOG_LEVEL` | `INFO` | Logging level |

## Architecture

**Data flow:** Camera → MediaPipe → GestureEngine → GestureSmoother → DepthSmoother → Pipeline → (Controller + IntentEngine + ActionEngine + Scene) → WebSocket → Three.js

**Key design decisions:**
- Backend is the sole authority for spatial state; frontend only renders
- Per-session isolation: each WebSocket client gets its own Pipeline, GestureSmoother, DepthSmoother, ProtocolHandler
- LLM is injectable/optional — system works fully without one
- Pipeline handles all orchestration; main.py is thin
- Protocol supports handshake, version negotiation, ping/pong keepalive

## Gesture Controls

| Gesture | Description |
|---------|-------------|
| **PINCH** | Thumb and index finger close together — grab objects |
| **OPEN_PALM** | All four fingers extended — release objects |
| **POINT** | Only index finger extended — point at objects |
| **FIST** | No fingers extended |
| **RELAXED** | 1-3 fingers extended (partial hand) |
| **UNKNOWN** | Unrecognized or transitioning state |

## Interaction Model

| State | Description |
|-------|-------------|
| **IDLE** | No hand near object |
| **HOVERED** | Hand over object (cursor highlight) |
| **SELECTED** | Object selected but not grabbed |
| **GRABBED** | Object being held and moved |
| **CLICK** | Short pinch at same position |
| **DOUBLE_CLICK** | Two quick clicks |
| **FREEZE** | Grab held still for >1 second |
| **RESUME** | Movement resumes after freeze |
