"""Entity system for minepy - equivalent to prismarine-entity."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from minepy.vec3 import Vec3

if TYPE_CHECKING:
    from minepy.types import Effect


class EntityType(str, Enum):
    """Entity type categories."""

    PLAYER = "player"
    MOB = "mob"
    OBJECT = "object"
    GLOBAL = "global"
    OTHER = "other"


class EntityCategory(str, Enum):
    """Entity categories for behavior."""

    HOSTILE = "hostile"
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    TAMABLE = "tamable"
    UTILITY = "utility"
    BOSS = "boss"
    UNKNOWN = "unknown"


@dataclass
class Equipment:
    """Entity equipment slots."""

    main_hand: Item | None = None
    off_hand: Item | None = None
    helmet: Item | None = None
    chestplate: Item | None = None
    leggings: Item | None = None
    boots: Item | None = None


@dataclass
class Item:
    """Item in entity equipment or inventory."""

    id: int
    name: str = ""
    display_name: str = ""
    count: int = 1
    metadata: int = 0
    nbt: dict[str, Any] | None = None
    durability: int | None = None
    max_durability: int | None = None
    enchantments: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Item:
        """Create Item from dictionary."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            display_name=data.get("displayName", data.get("name", "")),
            count=data.get("count", 1),
            metadata=data.get("metadata", 0),
            nbt=data.get("nbt"),
            durability=data.get("durability"),
            max_durability=data.get("maxDurability"),
        )


@dataclass
class Entity:
    """
    Represents a Minecraft entity (player, mob, object, etc.).

    Attributes:
        id: Unique entity ID from server
        uuid: Entity UUID (for players and some mobs)
        type: Entity type category
        name: Entity name (e.g., "zombie", "player")
        display_name: Human-readable name
    """

    # Identification
    id: int
    uuid: str | None = None
    type: EntityType = EntityType.OTHER
    entity_type_id: int | None = None
    name: str = ""
    display_name: str = ""
    custom_name: str | None = None

    # Position and movement
    position: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    velocity: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))
    yaw: float = 0.0
    pitch: float = 0.0
    head_yaw: float = 0.0
    on_ground: bool = True

    # Physical properties
    height: float = 1.8
    width: float = 0.6
    eye_height: float = 1.62

    # Health and status
    health: float = 20.0
    max_health: float = 20.0
    absorption: float = 0.0

    # Equipment
    equipment: Equipment = field(default_factory=Equipment)

    # Metadata
    metadata: dict[int, Any] = field(default_factory=dict)

    # Effects
    effects: list[Effect] = field(default_factory=list)

    # Player-specific
    username: str | None = None
    gamemode: int | None = None
    ping: int | None = None
    skin_data: dict | None = None

    # Mob-specific
    is_baby: bool = False
    is_angry: bool = False
    is_tamed: bool = False
    owner_uuid: str | None = None

    # Vehicle
    vehicle: Entity | None = None
    passengers: list[Entity] = field(default_factory=list)

    # Item-specific (for dropped items)
    item: Item | None = None
    pickup_delay: int = 0

    # Object-specific
    object_data: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Entity:
        """Create Entity from dictionary."""
        position = Vec3.from_dict(data.get("position", {}))
        velocity = Vec3.from_dict(data.get("velocity", {}))

        entity = cls(
            id=data.get("id", 0),
            uuid=data.get("uuid"),
            name=data.get("name", data.get("type", "")),
            display_name=data.get("displayName", data.get("name", "")),
            position=position,
            velocity=velocity,
            yaw=data.get("yaw", 0.0),
            pitch=data.get("pitch", 0.0),
            on_ground=data.get("onGround", True),
            height=data.get("height", 1.8),
            width=data.get("width", 0.6),
            health=data.get("health", 20.0),
            max_health=data.get("maxHealth", 20.0),
            username=data.get("username"),
            gamemode=data.get("gamemode"),
            ping=data.get("ping"),
        )

        # Parse equipment if present
        if "equipment" in data:
            eq = data["equipment"]
            entity.equipment = Equipment(
                main_hand=Item.from_dict(eq["mainHand"]) if eq.get("mainHand") else None,
                off_hand=Item.from_dict(eq["offHand"]) if eq.get("offHand") else None,
                helmet=Item.from_dict(eq["helmet"]) if eq.get("helmet") else None,
                chestplate=Item.from_dict(eq["chestplate"]) if eq.get("chestplate") else None,
                leggings=Item.from_dict(eq["leggings"]) if eq.get("leggings") else None,
                boots=Item.from_dict(eq["boots"]) if eq.get("boots") else None,
            )

        return entity

    # ==================== Type Checks ====================

    def is_player(self) -> bool:
        """Check if entity is a player."""
        return self.type == EntityType.PLAYER or self.username is not None

    def is_mob(self) -> bool:
        """Check if entity is a mob."""
        return self.type == EntityType.MOB

    def is_object(self) -> bool:
        """Check if entity is an object (item, arrow, etc.)."""
        return self.type == EntityType.OBJECT

    def is_item(self) -> bool:
        """Check if entity is a dropped item."""
        return self.name == "item" or self.item is not None

    def is_vehicle(self) -> bool:
        """Check if entity can be ridden."""
        return self.name in (
            "boat",
            "minecart",
            "horse",
            "donkey",
            "mule",
            "llama",
            "pig",
            "strider",
            "camel",
            "raft",
        )

    def is_hostile(self) -> bool:
        """Check if entity is likely hostile."""
        hostile_names = {
            "zombie",
            "skeleton",
            "spider",
            "cave_spider",
            "creeper",
            "enderman",
            "witch",
            "slime",
            "phantom",
            "drowned",
            "husk",
            "stray",
            "wither_skeleton",
            "blaze",
            "ghast",
            "magma_cube",
            "endermite",
            "silverfish",
            "guardian",
            "elder_guardian",
            "shulker",
            "vindicator",
            "evoker",
            "pillager",
            "ravager",
            "hoglin",
            "zoglin",
            "piglin_brute",
            "warden",
            "breeze",
        }
        return self.name in hostile_names

    def is_passive(self) -> bool:
        """Check if entity is passive."""
        passive_names = {
            "pig",
            "cow",
            "sheep",
            "chicken",
            "rabbit",
            "mooshroom",
            "squid",
            "glow_squid",
            "bat",
            "parrot",
            "cod",
            "salmon",
            "tropical_fish",
            "pufferfish",
            "turtle",
            "dolphin",
            "fox",
            "panda",
            "bee",
            "strider",
            "axolotl",
            "goat",
            "frog",
            "tadpole",
            "allay",
            "sniffer",
            "armadillo",
        }
        return self.name in passive_names

    def is_neutral(self) -> bool:
        """Check if entity is neutral (attacks only when provoked)."""
        neutral_names = {
            "wolf",
            "polar_bear",
            "llama",
            "trader_llama",
            "panda",
            "bee",
            "dolphin",
            "iron_golem",
            "snow_golem",
        }
        return self.name in neutral_names

    # ==================== Distance Calculations ====================

    def distance_to(self, other: Entity | Vec3) -> float:
        """Get Euclidean distance to another entity or position."""
        if isinstance(other, Entity):
            return self.position.distance_to(other.position)
        return self.position.distance_to(other)

    def distance_to_squared(self, other: Entity | Vec3) -> float:
        """Get squared distance (faster than distance_to)."""
        if isinstance(other, Entity):
            return self.position.distance_to_squared(other.position)
        return self.position.distance_to_squared(other)

    def horizontal_distance_to(self, other: Entity | Vec3) -> float:
        """Get horizontal distance (ignoring Y coordinate)."""
        if isinstance(other, Entity):
            return self.position.horizontal_distance_to(other.position)
        return self.position.horizontal_distance_to(other)

    def is_within_distance(self, other: Entity | Vec3, distance: float) -> bool:
        """Check if within a certain distance."""
        return self.distance_to_squared(other) <= distance * distance

    # ==================== Position Helpers ====================

    def get_eye_position(self) -> Vec3:
        """Get the eye position of the entity."""
        return self.position.offset(0, self.eye_height, 0)

    def get_feet_position(self) -> Vec3:
        """Get the feet position (same as position for most entities)."""
        return self.position

    def get_bounding_box(self) -> tuple[Vec3, Vec3]:
        """Get the bounding box as (min_corner, max_corner)."""
        half_width = self.width / 2
        return (
            Vec3(self.position.x - half_width, self.position.y, self.position.z - half_width),
            Vec3(
                self.position.x + half_width,
                self.position.y + self.height,
                self.position.z + half_width,
            ),
        )

    # ==================== Look Direction ====================

    def get_look_vector(self) -> Vec3:
        """Get the direction the entity is looking."""
        yaw_rad = math.radians(-self.yaw)
        pitch_rad = math.radians(-self.pitch)

        x = math.sin(yaw_rad) * math.cos(pitch_rad)
        y = math.sin(pitch_rad)
        z = math.cos(yaw_rad) * math.cos(pitch_rad)

        return Vec3(-x, -y, z).normalize()

    def get_look_yaw_pitch(self, target: Vec3) -> tuple[float, float]:
        """Calculate yaw and pitch to look at target position."""
        direction = target - self.get_eye_position()
        return self._direction_to_yaw_pitch(direction)

    def _direction_to_yaw_pitch(self, direction: Vec3) -> tuple[float, float]:
        """Convert direction vector to yaw and pitch."""
        horizontal_dist = math.sqrt(direction.x**2 + direction.z**2)

        yaw = math.degrees(math.atan2(-direction.x, direction.z))
        pitch = math.degrees(math.atan2(-direction.y, horizontal_dist))

        return yaw, pitch

    # ==================== Equipment Helpers ====================

    def get_held_item(self) -> Item | None:
        """Get the item in the main hand."""
        return self.equipment.main_hand

    def get_off_hand_item(self) -> Item | None:
        """Get the item in the off hand."""
        return self.equipment.off_hand

    def get_armor(self) -> list[Item | None]:
        """Get all armor pieces as a list."""
        return [
            self.equipment.helmet,
            self.equipment.chestplate,
            self.equipment.leggings,
            self.equipment.boots,
        ]

    # ==================== Effect Helpers ====================

    def has_effect(self, effect_id: int) -> bool:
        """Check if entity has a specific effect."""
        return any(e.get("id") == effect_id for e in self.effects)

    def get_effect(self, effect_id: int) -> dict | None:
        """Get effect details if present."""
        for effect in self.effects:
            if effect.get("id") == effect_id:
                return effect
        return None

    def get_effect_amplifier(self, effect_id: int) -> int:
        """Get amplifier level of effect (0 for no effect)."""
        effect = self.get_effect(effect_id)
        return effect.get("amplifier", 0) if effect else 0

    # ==================== String Representation ====================

    def __repr__(self) -> str:
        name = self.username or self.display_name or self.name or f"Entity({self.id})"
        return f"Entity(id={self.id}, name={name}, pos={self.position})"

    def __str__(self) -> str:
        return self.display_name or self.name or f"Entity({self.id})"


# Entity type mappings (common entities)
ENTITY_TYPES: dict[str, dict] = {
    # Players
    "player": {"type": EntityType.PLAYER, "height": 1.8, "width": 0.6, "eye_height": 1.62},
    # Hostile Mobs
    "zombie": {"type": EntityType.MOB, "height": 1.95, "width": 0.6, "eye_height": 1.74},
    "skeleton": {"type": EntityType.MOB, "height": 1.99, "width": 0.6, "eye_height": 1.74},
    "creeper": {"type": EntityType.MOB, "height": 1.7, "width": 0.6, "eye_height": 1.5},
    "spider": {"type": EntityType.MOB, "height": 0.9, "width": 1.4, "eye_height": 0.65},
    "enderman": {"type": EntityType.MOB, "height": 2.9, "width": 0.6, "eye_height": 2.55},
    "witch": {"type": EntityType.MOB, "height": 1.95, "width": 0.6, "eye_height": 1.62},
    "blaze": {"type": EntityType.MOB, "height": 1.8, "width": 0.6, "eye_height": 1.62},
    "ghast": {"type": EntityType.MOB, "height": 4.0, "width": 4.0, "eye_height": 3.5},
    # Passive Mobs
    "pig": {"type": EntityType.MOB, "height": 0.9, "width": 0.9, "eye_height": 0.7},
    "cow": {"type": EntityType.MOB, "height": 1.4, "width": 0.9, "eye_height": 1.1},
    "sheep": {"type": EntityType.MOB, "height": 1.3, "width": 0.9, "eye_height": 1.0},
    "chicken": {"type": EntityType.MOB, "height": 0.7, "width": 0.4, "eye_height": 0.5},
    "rabbit": {"type": EntityType.MOB, "height": 0.5, "width": 0.4, "eye_height": 0.35},
    # Neutral Mobs
    "wolf": {"type": EntityType.MOB, "height": 0.85, "width": 0.6, "eye_height": 0.68},
    "iron_golem": {"type": EntityType.MOB, "height": 2.7, "width": 1.4, "eye_height": 2.35},
    # Objects
    "item": {"type": EntityType.OBJECT, "height": 0.25, "width": 0.25, "eye_height": 0.125},
    "arrow": {"type": EntityType.OBJECT, "height": 0.5, "width": 0.5, "eye_height": 0.25},
    "boat": {"type": EntityType.OBJECT, "height": 0.5625, "width": 1.375, "eye_height": 0.5},
    "minecart": {"type": EntityType.OBJECT, "height": 0.7, "width": 0.98, "eye_height": 0.5},
    "falling_block": {"type": EntityType.OBJECT, "height": 0.98, "width": 0.98, "eye_height": 0.49},
    "tnt": {"type": EntityType.OBJECT, "height": 0.98, "width": 0.98, "eye_height": 0.49},
    # Vehicles
    "horse": {"type": EntityType.MOB, "height": 1.6, "width": 1.3965, "eye_height": 1.35},
    "donkey": {"type": EntityType.MOB, "height": 1.5, "width": 1.3965, "eye_height": 1.25},
    "mule": {"type": EntityType.MOB, "height": 1.6, "width": 1.3965, "eye_height": 1.35},
    "llama": {"type": EntityType.MOB, "height": 1.87, "width": 0.9, "eye_height": 1.57},
    "camel": {"type": EntityType.MOB, "height": 2.375, "width": 1.7, "eye_height": 2.0},
    "strider": {"type": EntityType.MOB, "height": 1.7, "width": 0.9, "eye_height": 1.4},
    # Bosses
    "ender_dragon": {"type": EntityType.MOB, "height": 8.0, "width": 16.0, "eye_height": 6.0},
    "wither": {"type": EntityType.MOB, "height": 3.5, "width": 0.9, "eye_height": 2.9},
    "warden": {"type": EntityType.MOB, "height": 2.9, "width": 0.9, "eye_height": 2.5},
}


def create_entity(entity_id: int, name: str, **kwargs) -> Entity:
    """
    Factory function to create an entity with proper dimensions.

    Args:
        entity_id: Server-assigned entity ID
        name: Entity type name (e.g., "zombie", "player")
        **kwargs: Additional entity properties

    Returns:
        Configured Entity instance
    """
    type_info = ENTITY_TYPES.get(name, {})

    return Entity(
        id=entity_id,
        name=name,
        type=type_info.get("type", EntityType.OTHER),
        height=kwargs.pop("height", type_info.get("height", 1.8)),
        width=kwargs.pop("width", type_info.get("width", 0.6)),
        eye_height=kwargs.pop("eye_height", type_info.get("eye_height", 1.62)),
        **kwargs,
    )
