"""
Minepy - Create Minecraft bots with a powerful, high-level Python API.

A Python equivalent of mineflayer, supporting Minecraft 1.8 through 1.21.x.
"""

from __future__ import annotations

from minepy.block import BLOCKS, Block, create_block

# Core classes
from minepy.bot import Bot, create_bot
from minepy.entity import (
    ENTITY_TYPES,
    Entity,
    EntityCategory,
    EntityType,
    Equipment,
    Item,
    create_entity,
)
from minepy.events import EVENT_NAMES, BotEvents
from minepy.inventory import Inventory, Slot, Window
from minepy.plugin import Plugin
from minepy.types import (
    AuthType,
    BotOptions,
    ChatLevel,
    Difficulty,
    Dimension,
    Effect,
    GameState,
    InventorySlot,
    Player,
    Position,
)

# Data classes
from minepy.vec3 import DOWN, EAST, FACES, NORTH, SOUTH, UP, WEST, Vec3
from minepy.world import Chunk, Section, World

__all__ = [# Core
    "Bot",
    "BotEvents",
    "BotOptions",
    "GameState",
    "Plugin",
    "create_bot",
    "EVENT_NAMES",
    # Types
    "AuthType",
    "ChatLevel",
    "Difficulty",
    "Dimension",
    "Effect",
    "InventorySlot",
    "Player",
    "Position",
    # Data classes
    "Vec3",
    "FACES",
    "UP",
    "DOWN",
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    # Block
    "Block",
    "BLOCKS",
    "create_block",
    # Entity
    "Entity",
    "EntityType",
    "EntityCategory",
    "Equipment",
    "Item",
    "ENTITY_TYPES",
    "create_entity",
    # World
    "World",
    "Chunk",
    "Section",
    "Scoreboard",
    "Team",
    "Physics",]

__version__ = "0.2.0"
