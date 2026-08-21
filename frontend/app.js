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
// Grid
// ─────────────────────────────────────────────

const grid = new THREE.GridHelper(
    10,
    20
);

grid.position.y = -1.2;

scene.add(grid);


// ─────────────────────────────────────────────
// Shadow disc (V1.7)
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
// Primary sphere (V1.4 legacy)
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
// V1.8: Scene object registry (frontend)
// ─────────────────────────────────────────────

const sceneObjects = {};
const objectMeshes = {};


function createObjectMesh(objData) {
    const type = objData.type;

    if (type === "SPHERE") {
        const geo = new THREE.SphereGeometry(0.7, 32, 32);
        const mat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(objData.color),
            roughness: 0.25,
            metalness: 0.4,
        });
        return new THREE.Mesh(geo, mat);
    }

    if (type === "PANEL") {
        const w = (objData.width || 2.0) * 0.5;
        const h = (objData.height || 1.2) * 0.5;
        const geo = new THREE.BoxGeometry(w, h, 0.04);
        const mat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(objData.color),
            roughness: 0.6,
            metalness: 0.1,
            transparent: true,
            opacity: objData.opacity || 0.85,
        });
        const mesh = new THREE.Mesh(geo, mat);

        if (objData.label) {
            const canvas = document.createElement("canvas");
            canvas.width = 256;
            canvas.height = 128;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "rgba(0,0,0,0)";
            ctx.fillRect(0, 0, 256, 128);
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 24px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(objData.label, 128, 64);
            const tex = new THREE.CanvasTexture(canvas);
            const labelMat = new THREE.MeshBasicMaterial({
                map: tex,
                transparent: true,
                side: THREE.DoubleSide,
            });
            const labelGeo = new THREE.PlaneGeometry(w * 0.9, h * 0.5);
            const labelMesh = new THREE.Mesh(labelGeo, labelMat);
            labelMesh.position.z = 0.025;
            mesh.add(labelMesh);
        }
        return mesh;
    }

    if (type === "BUTTON") {
        const w = (objData.width || 0.6) * 0.5;
        const h = (objData.height || 0.3) * 0.5;
        const geo = new THREE.BoxGeometry(w, h, 0.08);
        const mat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(objData.color),
            roughness: 0.3,
            metalness: 0.3,
        });
        const mesh = new THREE.Mesh(geo, mat);

        if (objData.label) {
            const canvas = document.createElement("canvas");
            canvas.width = 128;
            canvas.height = 64;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 20px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(objData.label, 64, 32);
            const tex = new THREE.CanvasTexture(canvas);
            const labelMat = new THREE.MeshBasicMaterial({
                map: tex,
                transparent: true,
                side: THREE.DoubleSide,
            });
            const labelGeo = new THREE.PlaneGeometry(w * 0.8, h * 0.6);
            const labelMesh = new THREE.Mesh(labelGeo, labelMat);
            labelMesh.position.z = 0.045;
            mesh.add(labelMesh);
        }
        return mesh;
    }

    if (type === "CARD") {
        const w = (objData.width || 1.0) * 0.5;
        const h = (objData.height || 0.7) * 0.5;
        const geo = new THREE.BoxGeometry(w, h, 0.03);
        const mat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(objData.color),
            roughness: 0.5,
            metalness: 0.1,
            transparent: true,
            opacity: objData.opacity || 0.9,
        });
        const mesh = new THREE.Mesh(geo, mat);

        if (objData.label) {
            const canvas = document.createElement("canvas");
            canvas.width = 256;
            canvas.height = 180;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 20px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(objData.label, 128, 20);
            ctx.font = "14px Arial";
            ctx.fillStyle = "#aaaaaa";
            ctx.fillText("V2.0 Spatial UI", 128, 55);
            ctx.fillText("Drag to interact", 128, 80);
            const tex = new THREE.CanvasTexture(canvas);
            const labelMat = new THREE.MeshBasicMaterial({
                map: tex,
                transparent: true,
                side: THREE.DoubleSide,
            });
            const labelGeo = new THREE.PlaneGeometry(w * 0.9, h * 0.8);
            const labelMesh = new THREE.Mesh(labelGeo, labelMat);
            labelMesh.position.z = 0.02;
            mesh.add(labelMesh);
        }
        return mesh;
    }

    return null;
}


const STATE_COLORS = {
    "DEFAULT": null,
    "HOVERED": 0x4488ff,
    "SELECTED": 0xffff44,
    "GRABBED": 0x00ffcc,
};

const STATE_EMISSIVE = {
    "DEFAULT": 0x000000,
    "HOVERED": 0x112244,
    "SELECTED": 0x333300,
    "GRABBED": 0x003322,
};


function updateObjectVisuals(mesh, objData) {
    if (!mesh || !mesh.material) return;
    const state = objData.state || "DEFAULT";

    if (mesh.material.color) {
        const baseColor = new THREE.Color(objData.color);
        const stateColor = STATE_COLORS[state];
        if (stateColor !== null) {
            const highlightColor = new THREE.Color(stateColor);
            mesh.material.color.copy(baseColor).lerp(highlightColor, 0.3);
        } else {
            mesh.material.color.copy(baseColor);
        }
    }

    if (mesh.material.emissive) {
        mesh.material.emissive.setHex(STATE_EMISSIVE[state] || 0x000000);
    }

    const isHovered = state === "HOVERED";
    const isSelected = state === "SELECTED";
    const isGrabbed = state === "GRABBED";
    mesh.scale.setScalar(isHovered ? 1.05 : (isGrabbed ? 0.95 : 1.0));
}


function syncSceneObjects(sceneData) {
    if (!sceneData || !sceneData.objects) return;

    const activeIds = new Set();

    for (const objData of sceneData.objects) {
        const id = objData.id;
        activeIds.add(id);

        if (objData.type === "SPHERE" && id === "sphere") {
            continue;
        }

        if (!objectMeshes[id]) {
            const mesh = createObjectMesh(objData);
            if (mesh) {
                mesh.position.set(objData.x, objData.y, objData.z);
                scene.add(mesh);
                objectMeshes[id] = mesh;
            }
        }

        const mesh = objectMeshes[id];
        if (mesh) {
            mesh.position.x += (objData.x - mesh.position.x) * 0.15;
            mesh.position.y += (objData.y - mesh.position.y) * 0.15;
            mesh.position.z += (objData.z - mesh.position.z) * 0.15;

            if (objData.type !== "SPHERE") {
                mesh.rotation.z +=
                    (objData.rotation - mesh.rotation.z) * 0.15;
            }

            updateObjectVisuals(mesh, objData);
        }
    }

    for (const id of Object.keys(objectMeshes)) {
        if (!activeIds.has(id)) {
            scene.remove(objectMeshes[id]);
            delete objectMeshes[id];
        }
    }
}


// ─────────────────────────────────────────────
// Spatial cursors (V1.8)
// ─────────────────────────────────────────────

const spatialCursorGeometry = new THREE.SphereGeometry(
    0.04,
    12,
    12
);

const spatialCursorMaterials = {
    "LEFT": new THREE.MeshStandardMaterial({
        color: 0xff6666,
        roughness: 0.4,
        emissive: 0x220000,
    }),
    "RIGHT": new THREE.MeshStandardMaterial({
        color: 0x6666ff,
        roughness: 0.4,
        emissive: 0x000022,
    }),
};

const spatialCursors = {};

function syncSpatialCursors(cursorsData) {
    if (!cursorsData) return;

    for (const [label, cdata] of Object.entries(cursorsData)) {
        if (!spatialCursors[label]) {
            const mat = spatialCursorMaterials[label] || spatialCursorMaterials["LEFT"];
            spatialCursors[label] = new THREE.Mesh(
                spatialCursorGeometry, mat.clone()
            );
            scene.add(spatialCursors[label]);
        }
        const cursor = spatialCursors[label];
        if (cdata.active) {
            cursor.visible = true;
            cursor.position.x = (cdata.x - 0.5) * 6;
            cursor.position.y = -(cdata.y - 0.5) * 4;
            cursor.position.z = cdata.z || 0;
        } else {
            cursor.visible = false;
        }
    }
}


// ─────────────────────────────────────────────
// WebSocket
// ─────────────────────────────────────────────

let socket;

const PROTOCOL_VERSION = "2.0";

function connect() {

    socket = new WebSocket(
        "ws://127.0.0.1:8000/ws"
    );

    socket.onopen = () => {
        statusElement.textContent = "Connected, handshaking...";
        socket.send(JSON.stringify({
            type: "handshake",
            version: PROTOCOL_VERSION,
            capabilities: ["state_update", "events", "intents"],
        }));
    };


    socket.onclose = () => {
        statusElement.textContent = "Disconnected, reconnecting...";
        setTimeout(connect, 1000);
    };


    socket.onerror = () => {
        statusElement.textContent = "Connection error";
    };


    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "handshake_ack") {
            statusElement.textContent = `Connected V${data.version}`;
            return;
        }

        if (data.type === "pong") {
            return;
        }

        if (data.type === "error") {
            console.warn("Server error:", data.error);
            return;
        }

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


        if (data.events && data.events.length > 0) {

            const names = data.events.map(
                (e) => {
                    const label = e.hand_label ? `[${e.hand_label}]` : "";
                    return `${label}${e.type}`;
                }
            );

            eventsElement.textContent =
                `Events: ${names.join(", ")}`;

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


        if (data.scene) {
            syncSceneObjects(data.scene);
            syncSpatialCursors(data.scene.cursors);
        }
    };
}

connect();

setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ping" }));
    }
}, 30000);


// ─────────────────────────────────────────────
// Animation
// ─────────────────────────────────────────────

function animate() {

    requestAnimationFrame(
        animate
    );

    sphere.position.x +=
        (targetX - sphere.position.x) * 0.15;

    sphere.position.y +=
        (targetY - sphere.position.y) * 0.15;

    sphere.position.z +=
        (targetZ - sphere.position.z) * 0.15;

    const currentScale = sphere.scale.x;
    const newScale = currentScale + (targetScale - currentScale) * 0.15;
    sphere.scale.set(newScale, newScale, newScale);

    if (interactionState === "TWO_HAND") {
        sphere.rotation.z +=
            (targetRotation - sphere.rotation.z) * 0.15;
    }


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


    if (interactionState === "IDLE") {

        sphere.rotation.x += 0.003;
        sphere.rotation.y += 0.005;

    }


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
