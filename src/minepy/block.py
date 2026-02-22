"""Block class for minepy - equivalent to prismarine-block."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from minepy.vec3 import Vec3

if TYPE_CHECKING:
    pass


@dataclass
class Block:
    """
    Represents a block in the Minecraft world.

    Attributes:
        id: Block ID (numeric)
        name: Block name (e.g., "stone", "dirt")
        display_name: Human-readable name
        position: Block position in the world
    """

    # Identification
    id: int
    name: str = ""
    display_name: str = ""

    # Position
    position: Vec3 = field(default_factory=lambda: Vec3(0, 0, 0))

    # State
    metadata: int = 0
    state_id: int = 0
    properties: dict[str, Any] = field(default_factory=dict)

    # Physical properties
    hardness: float = 1.0
    blast_resistance: float = 1.0
    slipperiness: float = 0.6

    # Block type flags
    is_solid: bool = True
    is_liquid: bool = False
    is_transparent: bool = False
    is_air: bool = False
    is_flammable: bool = False

    # Interaction properties
    diggable: bool = True
    light_emission: int = 0
    light_filter: int = 15

    # Bounding box
    bounding_box: str = "block"  # "block", "empty", or custom shapes
    shapes: list[list[float]] = field(default_factory=lambda: [[0, 0, 0, 1, 1, 1]])

    # Block entity data
    block_entity: dict[str, Any] | None = None

    # Drops
    drops: list[dict] = field(default_factory=list)
    harvest_tools: dict[int, int] | None = None  # tool_id -> level
    material: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Block:
        """Create Block from dictionary."""
        position = Vec3.from_dict(data.get("position", {}))

        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            display_name=data.get("displayName", data.get("name", "")),
            position=position,
            metadata=data.get("metadata", 0),
            state_id=data.get("stateId", 0),
            properties=data.get("properties", {}),
            hardness=data.get("hardness", 1.0),
            blast_resistance=data.get("blastResistance", 1.0),
            is_solid=data.get("solid", True),
            is_liquid=data.get("liquid", False),
            is_transparent=data.get("transparent", False),
            is_air=data.get("air", False),
            diggable=data.get("dig", True),
            light_emission=data.get("lightEmission", 0),
            light_filter=data.get("lightFilter", 15),
            bounding_box=data.get("boundingBox", "block"),
            shapes=data.get("shapes", [[0, 0, 0, 1, 1, 1]]),
            block_entity=data.get("blockEntity"),
            drops=data.get("drops", []),
            harvest_tools=data.get("harvestTools"),
            material=data.get("material"),
        )

    @classmethod
    def create_air(cls, position: Vec3) -> Block:
        """Create an air block."""
        return cls(
            id=0,
            name="air",
            display_name="Air",
            position=position,
            is_solid=False,
            is_transparent=True,
            is_air=True,
            hardness=0.0,
            diggable=False,
            bounding_box="empty",
            shapes=[],
        )

    # ==================== Position Helpers ====================

    @property
    def x(self) -> int:
        return int(self.position.x)

    @property
    def y(self) -> int:
        return int(self.position.y)

    @property
    def z(self) -> int:
        return int(self.position.z)

    @property
    def chunk_x(self) -> int:
        """Get chunk X coordinate."""
        return self.x >> 4

    @property
    def chunk_z(self) -> int:
        """Get chunk Z coordinate."""
        return self.z >> 4

    @property
    def section_y(self) -> int:
        """Get section Y coordinate within chunk."""
        return self.y & 15

    # ==================== Block State Helpers ====================

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a block state property."""
        return self.properties.get(key, default)

    def get_facing(self) -> str:
        """Get facing direction (for directional blocks)."""
        return self.get_property("facing", "north")

    def get_half(self) -> str:
        """Get half (top/bottom for slabs, stairs)."""
        return self.get_property("half", "bottom")

    def get_type(self) -> str:
        """Get block type variant."""
        return self.get_property("type", "normal")

    def get_power(self) -> int:
        """Get redstone power level."""
        return self.get_property("power", 0)

    def is_powered(self) -> bool:
        """Check if block is powered."""
        return self.get_property("powered", False)

    def is_open(self) -> bool:
        """Check if block is open (doors, trapdoors, etc.)."""
        return self.get_property("open", False)

    def is_waterlogged(self) -> bool:
        """Check if block is waterlogged."""
        return self.get_property("waterlogged", False)

    def get_age(self) -> int:
        """Get age (for crops)."""
        return self.get_property("age", 0)

    def is_fully_grown(self) -> bool:
        """Check if crop is fully grown."""
        max_age = 7  # Most crops have max age 7
        return self.get_age() >= max_age

    # ==================== Type Checks ====================

    def is_bed(self) -> bool:
        """Check if block is a bed."""
        return self.name.endswith("_bed") or self.name == "bed"

    def is_chest(self) -> bool:
        """Check if block is a chest."""
        return self.name.endswith("_chest") or self.name == "chest"

    def is_shulker_box(self) -> bool:
        """Check if block is a shulker box."""
        return "shulker_box" in self.name

    def is_barrel(self) -> bool:
        """Check if block is a barrel."""
        return self.name == "barrel"

    def is_furnace(self) -> bool:
        """Check if block is a furnace or blast furnace."""
        return self.name in ("furnace", "blast_furnace", "smoker")

    def is_crafting_table(self) -> bool:
        """Check if block is a crafting table."""
        return self.name == "crafting_table"

    def is_container(self) -> bool:
        """Check if block can hold items."""
        return (
            self.is_chest()
            or self.is_shulker_box()
            or self.is_barrel()
            or self.is_furnace()
            or self.name in ("hopper", "dispenser", "dropper", "brewing_stand")
        )

    def is_fence(self) -> bool:
        """Check if block is a fence."""
        return "fence" in self.name and "fence_gate" not in self.name

    def is_fence_gate(self) -> bool:
        """Check if block is a fence gate."""
        return "fence_gate" in self.name

    def is_door(self) -> bool:
        """Check if block is a door."""
        return "_door" in self.name

    def is_trapdoor(self) -> bool:
        """Check if block is a trapdoor."""
        return "_trapdoor" in self.name

    def is_slab(self) -> bool:
        """Check if block is a slab."""
        return "_slab" in self.name

    def is_stairs(self) -> bool:
        """Check if block is stairs."""
        return "_stairs" in self.name

    def is_leaves(self) -> bool:
        """Check if block is leaves."""
        return "_leaves" in self.name

    def is_log(self) -> bool:
        """Check if block is a log/stem."""
        return any(x in self.name for x in ["_log", "_stem"])

    def is_ore(self) -> bool:
        """Check if block is an ore."""
        return "_ore" in self.name or self.name.endswith("ore")

    def is_crop(self) -> bool:
        """Check if block is a crop."""
        crop_names = {
            "wheat",
            "carrots",
            "potatoes",
            "beetroots",
            "melon_stem",
            "pumpkin_stem",
            "cocoa",
            "nether_wart",
            "sweet_berry_bush",
            "cactus",
            "sugar_cane",
            "bamboo",
        }
        return self.name in crop_names or self.name.endswith("_crop")

    def is_fluid(self) -> bool:
        """Check if block is a fluid (water or lava)."""
        return self.is_liquid or self.name in ("water", "lava", "flowing_water", "flowing_lava")

    def is_lava(self) -> bool:
        """Check if block is lava."""
        return "lava" in self.name

    def is_water(self) -> bool:
        """Check if block is water."""
        return "water" in self.name

    def is_passable(self) -> bool:
        """Check if the block can be walked through."""
        return not self.is_solid or self.is_liquid or self.is_air

    def can_interact(self) -> bool:
        """Check if the block has an interactive UI."""
        interactive = {
            "crafting_table",
            "furnace",
            "blast_furnace",
            "smoker",
            "anvil",
            "enchanting_table",
            "brewing_stand",
            "beacon",
            "hopper",
            "dispenser",
            "dropper",
            "loom",
            "cartography_table",
            "grindstone",
            "stonecutter",
            "smithing_table",
            "lectern",
        }
        return (
            self.name in interactive
            or self.is_container()
            or self.is_door()
            or self.is_fence_gate()
            or self.is_trapdoor()
            or self.is_bed()
        )

    # ==================== Sign Text ====================

    def get_sign_text(self) -> list[str]:
        """Get sign text (if block is a sign)."""
        if "sign" not in self.name or not self.block_entity:
            return []

        texts = []
        for i in range(1, 5):
            text_data = self.block_entity.get(f"Text{i}", "")
            if text_data:
                # Parse JSON text component (simplified)
                import json

                try:
                    parsed = json.loads(text_data)
                    texts.append(parsed.get("text", ""))
                except (json.JSONDecodeError, AttributeError):
                    texts.append(text_data)
            else:
                texts.append("")

        return texts

    # ==================== Utility ====================

    def __repr__(self) -> str:
        return f"Block({self.name}, pos={self.position})"

    def __str__(self) -> str:
        return self.display_name or self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Block):
            return self.id == other.id and self.position == other.position
        return False

    def __hash__(self) -> int:
        return hash((self.id, self.position.x, self.position.y, self.position.z))


# Common block definitions (minimal set for reference)
BLOCKS: dict[str, dict] = {
    "air": {"id": 0, "hardness": 0, "solid": False, "transparent": True, "air": True},
    "stone": {"id": 1, "hardness": 1.5, "material": "rock"},
    "grass_block": {"id": 2, "hardness": 0.6, "material": "earth"},
    "dirt": {"id": 3, "hardness": 0.5, "material": "earth"},
    "cobblestone": {"id": 4, "hardness": 2.0, "material": "rock"},
    "oak_planks": {"id": 5, "hardness": 2.0, "material": "wood", "flammable": True},
    "bedrock": {"id": 7, "hardness": -1, "dig": False, "material": "rock"},
    "water": {"id": 8, "hardness": 100, "solid": False, "liquid": True, "transparent": True},
    "lava": {"id": 10, "hardness": 100, "solid": False, "liquid": True, "lightEmission": 15},
    "sand": {"id": 12, "hardness": 0.5, "material": "sand"},
    "gravel": {"id": 13, "hardness": 0.6, "material": "sand"},
    "gold_ore": {"id": 14, "hardness": 3.0, "material": "rock"},
    "iron_ore": {"id": 15, "hardness": 3.0, "material": "rock"},
    "coal_ore": {"id": 16, "hardness": 3.0, "material": "rock"},
    "oak_log": {"id": 17, "hardness": 2.0, "material": "wood", "flammable": True},
    "leaves": {"id": 18, "hardness": 0.2, "transparent": True, "flammable": True},
    "diamond_ore": {"id": 56, "hardness": 3.0, "material": "rock"},
    "crafting_table": {"id": 58, "hardness": 2.5, "material": "wood"},
    "chest": {"id": 54, "hardness": 2.5, "material": "wood"},
    "furnace": {"id": 61, "hardness": 3.5, "material": "rock"},
    "obsidian": {"id": 49, "hardness": 50, "material": "rock"},
}


def create_block(block_id: int, position: Vec3, **kwargs) -> Block:
    """
    Factory function to create a block with proper properties.

    Args:
        block_id: Block ID
        position: Block position
        **kwargs: Additional properties

    Returns:
        Configured Block instance
    """
    # Find block info by ID
    block_info = None
    for name, info in BLOCKS.items():
        if info.get("id") == block_id:
            block_info = {**info, "name": name}
            break

    if block_info is None:
        block_info = {"id": block_id, "name": f"block_{block_id}"}

    return Block(
        id=block_id,
        name=block_info.get("name", ""),
        display_name=block_info.get("displayName", block_info.get("name", "")),
        position=position,
        hardness=kwargs.pop("hardness", block_info.get("hardness", 1.0)),
        is_solid=kwargs.pop("is_solid", block_info.get("solid", True)),
        is_liquid=kwargs.pop("is_liquid", block_info.get("liquid", False)),
        is_transparent=kwargs.pop("is_transparent", block_info.get("transparent", False)),
        is_air=kwargs.pop("is_air", block_info.get("air", False)),
        diggable=kwargs.pop("diggable", block_info.get("dig", True)),
        material=kwargs.pop("material", block_info.get("material")),
        **kwargs,
    )
