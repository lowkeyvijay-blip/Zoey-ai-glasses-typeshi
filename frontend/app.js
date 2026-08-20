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


// ─────────────────────────────────────────────
// Color palette for interaction states
// ─────────────────────────────────────────────

const COLOR_IDLE = 0x00aaff;
const COLOR_GRABBED = 0x00ffcc;
const COLOR_FLASH = 0xffff00;

let flashTimer = 0;
const FLASH_DURATION = 8;


// ─────────────────────────────────────────────
// Authoritative state from backend
// ─────────────────────────────────────────────

let targetX = 0;
let targetY = 0;
let interactionState = "IDLE";


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

        if (data.gesture) {

            gestureElement.textContent =
                `Gesture: ${data.gesture}`;
        }


        if (data.interaction_state) {

            interactionState =
                data.interaction_state;

            interactionElement.textContent =
                `State: ${interactionState}`;
        }


        // Backend-authoritative sphere position.

        if (
            data.sphere_x !== undefined &&
            data.sphere_y !== undefined
        ) {

            targetX = data.sphere_x;
            targetY = data.sphere_y;
        }


        // Interaction events

        if (data.events && data.events.length > 0) {

            const names = data.events.map(
                (e) => e.type
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


    // Sphere color feedback:
    //   - IDLE: blue
    //   - GRABBED: cyan-green
    //   - Flash (click): brief yellow override

    if (flashTimer > 0) {

        sphere.material.color.setHex(COLOR_FLASH);
        flashTimer--;

    } else if (interactionState === "GRABBED") {

        sphere.material.color.setHex(COLOR_GRABBED);

    } else {

        sphere.material.color.setHex(COLOR_IDLE);
    }


    // Auto-rotate only when IDLE.
    // Stop rotation during GRABBED for stability.

    if (interactionState !== "GRABBED") {

        sphere.rotation.x += 0.003;
        sphere.rotation.y += 0.005;

    }

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
