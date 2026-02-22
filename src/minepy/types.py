"""Type definitions for minepy."""

from __future__ import annotations

from enum import Enum
from typing import Literal, TypedDict, Unpack


class ChatLevel(str, Enum):
    ENABLED = "enabled"
    COMMANDS_ONLY = "commandsOnly"
    DISABLED = "disabled"


class GameMode(str, Enum):
    SURVIVAL = "survival"
    CREATIVE = "creative"
    ADVENTURE = "adventure"
    SPECTATOR = "spectator"


class Dimension(str, Enum):
    OVERWORLD = "minecraft:overworld"
    NETHER = "minecraft:the_nether"
    END = "minecraft:the_end"


class Difficulty(str, Enum):
    PEACEFUL = "peaceful"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class GameState(TypedDict):
    """Game state information."""

    game_mode: GameMode
    dimension: Dimension
    difficulty: Difficulty
    level_type: str
    hardcore: bool
    max_players: int
    server_brand: str


class AuthType(str, Enum):
    OFFLINE = "offline"
    MICROSOFT = "microsoft"


class BotOptions(TypedDict, total=False):
    """Options for creating a bot."""

    host: str
    port: int
    username: str
    password: str | None
    auth: Literal["offline", "microsoft"]
    version: str | None
    # Connection options
    connection_timeout: int
    keep_alive: bool
    # Behavior options
    hide_errors: bool
    log_errors: bool
    physics_enabled: bool
    # Plugin options
    load_internal_plugins: bool
    plugins: list[str]


class Position(TypedDict):
    """3D position."""

    x: float
    y: float
    z: float


class Player(TypedDict):
    """Player information."""

    uuid: str
    username: str
    display_name: str
    gamemode: int
    ping: int
    entity: int | None


class Effect(TypedDict):
    """Status effect."""

    id: int
    amplifier: int
    duration: int


class InventorySlot(TypedDict):
    """Inventory slot data."""

    slot: int
    item_id: int | None
    count: int
    metadata: int
    nbt: dict | None
