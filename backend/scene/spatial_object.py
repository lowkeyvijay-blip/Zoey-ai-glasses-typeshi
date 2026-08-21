"""Spatial object types for V1.8 scene system.

Defines the data model for all objects in the spatial scene:
position, rotation, scale, state, type, and visual properties.

Objects are pure data. The Scene manages the registry and
hit-testing. The frontend renders from serialized state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ObjectType(Enum):
    """Types of spatial objects."""
    SPHERE = "SPHERE"
    PANEL = "PANEL"
    BUTTON = "BUTTON"
    CARD = "CARD"


class ObjectState(Enum):
    """Visual/interaction state of a spatial object."""
    DEFAULT = "DEFAULT"
    HOVERED = "HOVERED"
    SELECTED = "SELECTED"
    GRABBED = "GRABBED"


@dataclass
class VisualProperties:
    """Visual appearance of a spatial object."""
    color: str = "#00aaff"
    opacity: float = 1.0
    label: str = ""
    width: float = 1.0
    height: float = 1.0


@dataclass
class SpatialObject:
    """A single object in the spatial scene.

    Attributes:
        id: Unique identifier.
        object_type: What kind of object.
        x, y, z: World-space position.
        rotation: Z-axis rotation in radians.
        scale: Uniform scale factor.
        state: Current interaction state.
        visual: Visual properties.
        hit_radius: Influence radius for hover detection.
    """
    id: str
    object_type: ObjectType = ObjectType.SPHERE
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    state: ObjectState = ObjectState.DEFAULT
    visual: VisualProperties = field(default_factory=VisualProperties)
    hit_radius: float = 0.8
    grabbed_by: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a dict for WebSocket transmission."""
        return {
            "id": self.id,
            "type": self.object_type.value,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "rotation": self.rotation,
            "scale": self.scale,
            "state": self.state.value,
            "color": self.visual.color,
            "opacity": self.visual.opacity,
            "label": self.visual.label,
            "width": self.visual.width,
            "height": self.visual.height,
            "hit_radius": self.hit_radius,
            "grabbed_by": self.grabbed_by,
        }


@dataclass
class SpatialCursor:
    """A cursor representing a tracked hand in 3D space."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    active: bool = False
    hand_label: str = ""

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "active": self.active,
            "hand_label": self.hand_label,
        }
