"""Scene registry for V1.8 spatial objects.

Manages the collection of spatial objects, provides hit-testing
for hover/select, and serializes full scene state for WebSocket.

The scene does NOT drive object movement — the controllers do.
The scene is the source of truth for object positions and states.
"""

from __future__ import annotations

import math
from typing import Optional

from backend.scene.spatial_object import (
    ObjectState,
    ObjectType,
    SpatialCursor,
    SpatialObject,
    VisualProperties,
)


class Scene:
    """Registry of spatial objects with hit-testing and serialization.

    The scene holds all objects. Controllers update object positions.
    The frontend reads serialized state each frame.
    """

    def __init__(self) -> None:
        self._objects: dict[str, SpatialObject] = {}
        self._cursors: dict[str, SpatialCursor] = {}
        self._next_id: int = 0

    @property
    def objects(self) -> dict[str, SpatialObject]:
        return self._objects

    @property
    def cursors(self) -> dict[str, SpatialCursor]:
        return self._cursors

    def _generate_id(self, prefix: str = "obj") -> str:
        self._next_id += 1
        return f"{prefix}_{self._next_id}"

    # ── Object management ──────────────────────────

    def add_object(
        self,
        object_type: ObjectType = ObjectType.SPHERE,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        rotation: float = 0.0,
        scale: float = 1.0,
        visual: Optional[VisualProperties] = None,
        hit_radius: float = 0.8,
        obj_id: Optional[str] = None,
    ) -> SpatialObject:
        """Add a new object to the scene. Returns the created object."""
        oid = obj_id or self._generate_id(
            object_type.value.lower()
        )
        obj = SpatialObject(
            id=oid,
            object_type=object_type,
            x=x,
            y=y,
            z=z,
            rotation=rotation,
            scale=scale,
            visual=visual or VisualProperties(),
            hit_radius=hit_radius,
        )
        self._objects[oid] = obj
        return obj

    def remove_object(self, obj_id: str) -> bool:
        """Remove an object by id. Returns True if found and removed."""
        if obj_id in self._objects:
            del self._objects[obj_id]
            return True
        return False

    def get_object(self, obj_id: str) -> Optional[SpatialObject]:
        return self._objects.get(obj_id)

    def update_object(
        self,
        obj_id: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        rotation: Optional[float] = None,
        scale: Optional[float] = None,
        state: Optional[ObjectState] = None,
        visual: Optional[VisualProperties] = None,
    ) -> bool:
        """Update properties of an existing object."""
        obj = self._objects.get(obj_id)
        if obj is None:
            return False
        if x is not None:
            obj.x = x
        if y is not None:
            obj.y = y
        if z is not None:
            obj.z = z
        if rotation is not None:
            obj.rotation = rotation
        if scale is not None:
            obj.scale = scale
        if state is not None:
            obj.state = state
        if visual is not None:
            obj.visual = visual
        return True

    # ── Cursor management ──────────────────────────

    def update_cursor(
        self,
        hand_label: str,
        x: float,
        y: float,
        z: float,
        active: bool = True,
    ) -> None:
        """Update or create a spatial cursor for a hand."""
        self._cursors[hand_label] = SpatialCursor(
            x=x, y=y, z=z, active=active, hand_label=hand_label
        )

    def clear_cursor(self, hand_label: str) -> None:
        """Mark a cursor as inactive."""
        if hand_label in self._cursors:
            self._cursors[hand_label].active = False

    # ── Hit-testing ────────────────────────────────

    def hit_test(
        self,
        cursor_x: float,
        cursor_y: float,
        cursor_z: float,
    ) -> Optional[SpatialObject]:
        """Find the closest object within hit_radius of cursor position.

        Uses 3D Euclidean distance. Returns the closest object
        within range, or None if nothing is close enough.
        """
        closest: Optional[SpatialObject] = None
        closest_dist = float("inf")

        for obj in self._objects.values():
            dx = obj.x - cursor_x
            dy = obj.y - cursor_y
            dz = obj.z - cursor_z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            effective_radius = obj.hit_radius * obj.scale
            if dist <= effective_radius and dist < closest_dist:
                closest = obj
                closest_dist = dist

        return closest

    def update_hover_states(
        self,
        cursor_x: float,
        cursor_y: float,
        cursor_z: float,
    ) -> Optional[str]:
        """Update hover states for all objects based on cursor position.

        Returns the id of the hovered object, or None.
        Objects that are GRABBED are never changed to HOVERED.
        """
        hovered = self.hit_test(cursor_x, cursor_y, cursor_z)
        hovered_id = None

        for obj in self._objects.values():
            if obj.state == ObjectState.GRABBED:
                continue
            if obj.state == ObjectState.SELECTED:
                continue
            if hovered is not None and obj.id == hovered.id:
                obj.state = ObjectState.HOVERED
                hovered_id = obj.id
            elif obj.state == ObjectState.HOVERED:
                obj.state = ObjectState.DEFAULT

        return hovered_id

    # ── Serialization ──────────────────────────────

    def serialize(self) -> dict:
        """Serialize full scene state for WebSocket transmission."""
        return {
            "objects": [
                obj.to_dict() for obj in self._objects.values()
            ],
            "cursors": {
                label: cursor.to_dict()
                for label, cursor in self._cursors.items()
            },
        }
