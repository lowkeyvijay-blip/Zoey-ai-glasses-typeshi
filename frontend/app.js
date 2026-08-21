import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";


// ─────────────────────────────────────────────
// Scene
// ─────────────────────────────────────────────

const scene = new THREE.Scene();

scene.background = new THREE.Color(0x05070b);


// Camera

const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    100
);

camera.position.z = 5;


// Renderer

const renderer = new THREE.WebGLRenderer({
    antialias: true
});

renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(
    window.innerWidth,
    window.innerHeight
);

document.body.appendChild(renderer.domElement);


// ─────────────────────────────────────────────
// Lighting
// ─────────────────────────────────────────────

const ambientLight = new THREE.AmbientLight(
    0xffffff,
    1.5
);

scene.add(ambientLight);


const directionalLight = new THREE.DirectionalLight(
    0xffffff,
    2
);

directionalLight.position.set(
    3,
    5,
    4
);

scene.add(directionalLight);


// ─────────────────────────────────────────────
// Sphere
// ─────────────────────────────────────────────

const geometry = new THREE.SphereGeometry(
    0.7,
    64,
    64
);

const material = new THREE.MeshStandardMaterial({
    color: 0x00aaff,
    roughness: 0.25,
    metalness: 0.4
});

const sphere = new THREE.Mesh(
    geometry,
    material
);

scene.add(sphere);


// ─────────────────────────────────────────────
// Grid
// ─────────────────────────────────────────────

const grid = new THREE.GridHelper(
    10,
    20
);

grid.position.y = -1.2;

scene.add(grid);


// ─────────────────────────────────────────────
// Shadow disc (V1.7) — follows sphere XZ
// ─────────────────────────────────────────────

const shadowGeometry = new THREE.CircleGeometry(
    0.5,
    32
);

const shadowMaterial = new THREE.MeshBasicMaterial({
    color: 0x00aaff,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide,
});

const shadowDisc = new THREE.Mesh(
    shadowGeometry,
    shadowMaterial
);

shadowDisc.rotation.x = -Math.PI / 2;
shadowDisc.position.y = -1.19;

scene.add(shadowDisc);


// ─────────────────────────────────────────────
// Hand cursors (V1.6)
// ─────────────────────────────────────────────

const cursorGeometry = new THREE.SphereGeometry(
    0.05,
    16,
    16
);

const leftCursorMaterial = new THREE.MeshStandardMaterial({
    color: 0xff6666,
    roughness: 0.5
});

const rightCursorMaterial = new THREE.MeshStandardMaterial({
    color: 0x6666ff,
    roughness: 0.5
});

const leftCursor = new THREE.Mesh(cursorGeometry, leftCursorMaterial);
const rightCursor = new THREE.Mesh(cursorGeometry, rightCursorMaterial);

leftCursor.visible = false;
rightCursor.visible = false;

scene.add(leftCursor);
scene.add(rightCursor);


// ─────────────────────────────────────────────
// HUD Elements
// ─────────────────────────────────────────────

const statusElement =
    document.getElementById("status");

const gestureElement =
    document.getElementById("gesture");

const interactionElement =
    document.getElementById("interaction");

const eventsElement =
    document.getElementById("events");

const depthElement =
    document.getElementById("depth");


// ─────────────────────────────────────────────
// Color palette for interaction states
// ─────────────────────────────────────────────

const COLOR_IDLE = 0x00aaff;
const COLOR_GRABBED = 0x00ffcc;
const COLOR_TWO_HAND = 0xffaa00;
const COLOR_FLASH = 0xffff00;

let flashTimer = 0;
const FLASH_DURATION = 8;


// ─────────────────────────────────────────────
// Authoritative state from backend
// ─────────────────────────────────────────────

let targetX = 0;
let targetY = 0;
let targetZ = 0;
let targetScale = 1.0;
let targetRotation = 0;
let interactionState = "IDLE";

let leftHandPos = null;
let rightHandPos = null;
let leftState = "IDLE";
let rightState = "IDLE";


// ─────────────────────────────────────────────
// WebSocket
// ─────────────────────────────────────────────

let socket;

function connect() {

    socket = new WebSocket(
        "ws://127.0.0.1:8000/ws"
    );

    socket.onopen = () => {

        statusElement.textContent =
            "Vision connected";
    };


    socket.onclose = () => {

        statusElement.textContent =
            "Vision disconnected";

        setTimeout(
            connect,
            1000
        );
    };


    socket.onerror = () => {

        statusElement.textContent =
            "Connection error";
    };


    socket.onmessage = (event) => {

        const data =
            JSON.parse(event.data);

        // Per-hand gesture display

        const parts = [];
        if (data.left_state && data.left_state !== "IDLE") {
            parts.push(`L:${data.left_state}`);
        }
        if (data.right_state && data.right_state !== "IDLE") {
            parts.push(`R:${data.right_state}`);
        }

        if (data.interaction_state) {

            interactionState =
                data.interaction_state;

            interactionElement.textContent =
                `State: ${interactionState}` + (parts.length > 0 ? ` (${parts.join(", ")})` : "");
        }


        // Backend-authoritative sphere position + scale + rotation

        if (
            data.sphere_x !== undefined &&
            data.sphere_y !== undefined
        ) {

            targetX = data.sphere_x;
            targetY = data.sphere_y;
        }

        if (data.sphere_z !== undefined) {
            targetZ = data.sphere_z;
        }

        if (data.sphere_scale !== undefined) {
            targetScale = data.sphere_scale;
        }

        if (data.sphere_rotation !== undefined) {
            targetRotation = data.sphere_rotation;
        }


        // Hand cursors

        if (data.left_hand) {
            leftHandPos = data.left_hand;
            leftState = data.left_state;
            leftCursor.visible = true;
        } else {
            leftHandPos = null;
            leftCursor.visible = false;
        }

        if (data.right_hand) {
            rightHandPos = data.right_hand;
            rightState = data.right_state;
            rightCursor.visible = true;
        } else {
            rightHandPos = null;
            rightCursor.visible = false;
        }


        // Interaction events

        if (data.events && data.events.length > 0) {

            const names = data.events.map(
                (e) => {
                    const label = e.hand_label ? `[${e.hand_label}]` : "";
                    return `${label}${e.type}`;
                }
            );

            eventsElement.textContent =
                `Events: ${names.join(", ")}`;

            // Flash on CLICK or DOUBLE_CLICK

            const hasClick = data.events.some(
                (e) =>
                    e.type === "CLICK" ||
                    e.type === "DOUBLE_CLICK"
            );

            if (hasClick) {
                flashTimer = FLASH_DURATION;
            }

        } else {

            eventsElement.textContent =
                "Events: —";
        }
    };
}

connect();


// ─────────────────────────────────────────────
// Animation
// ─────────────────────────────────────────────

function animate() {

    requestAnimationFrame(
        animate
    );

    // Interpolate toward backend-authoritative position

    sphere.position.x +=
        (targetX - sphere.position.x) * 0.15;

    sphere.position.y +=
        (targetY - sphere.position.y) * 0.15;

    sphere.position.z +=
        (targetZ - sphere.position.z) * 0.15;

    // Interpolate scale

    const currentScale = sphere.scale.x;
    const newScale = currentScale + (targetScale - currentScale) * 0.15;
    sphere.scale.set(newScale, newScale, newScale);

    // Apply two-hand rotation

    if (interactionState === "TWO_HAND") {
        sphere.rotation.z +=
            (targetRotation - sphere.rotation.z) * 0.15;
    }


    // Sphere color feedback:
    //   - IDLE: blue
    //   - GRABBED: cyan-green
    //   - TWO_HAND: orange
    //   - Flash (click): brief yellow override

    if (flashTimer > 0) {

        sphere.material.color.setHex(COLOR_FLASH);
        flashTimer--;

    } else if (interactionState === "TWO_HAND") {

        sphere.material.color.setHex(COLOR_TWO_HAND);

    } else if (interactionState === "GRABBED") {

        sphere.material.color.setHex(COLOR_GRABBED);

    } else {

        sphere.material.color.setHex(COLOR_IDLE);
    }


    // Auto-rotate only when IDLE.
    // Stop rotation during GRABBED or TWO_HAND for stability.

    if (interactionState === "IDLE") {

        sphere.rotation.x += 0.003;
        sphere.rotation.y += 0.005;

    }


    // Hand cursors: map normalized coords to scene space

    if (leftHandPos) {
        leftCursor.position.x = (leftHandPos.x - 0.5) * 6;
        leftCursor.position.y = -(leftHandPos.y - 0.5) * 4;
        leftCursor.position.z = leftHandPos.z || 0;
    }

    if (rightHandPos) {
        rightCursor.position.x = (rightHandPos.x - 0.5) * 6;
        rightCursor.position.y = -(rightHandPos.y - 0.5) * 4;
        rightCursor.position.z = rightHandPos.z || 0;
    }


    // Shadow disc follows sphere XZ on the ground plane

    shadowDisc.position.x = sphere.position.x;
    shadowDisc.position.z = sphere.position.z;

    const shadowOpacity = 0.08 + Math.abs(sphere.position.z) * 0.04;
    shadowMaterial.opacity = Math.min(0.3, shadowOpacity);

    const shadowScale = 0.5 + Math.abs(sphere.position.z) * 0.25;
    shadowDisc.scale.set(shadowScale, shadowScale, 1);

    depthElement.textContent =
        `Depth: ${sphere.position.z.toFixed(2)}`;


    renderer.render(
        scene,
        camera
    );
}

animate();


// ─────────────────────────────────────────────
// Resize
// ─────────────────────────────────────────────

window.addEventListener(
    "resize",
    () => {

        camera.aspect =
            window.innerWidth /
            window.innerHeight;

        camera.updateProjectionMatrix();

        renderer.setSize(
            window.innerWidth,
            window.innerHeight
        );
    }
);
