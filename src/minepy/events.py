"""Event system for minepy."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

# Type alias for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class BotEvents:
    """
    Event definitions for bot events.

    Each method signature defines the arguments passed to event handlers.
    """

    # Connection events
    connect: Callable[[], None]  # () -> None
    inject_allowed: Callable[[], None]
    login: Callable[[], None]
    spawn: Callable[[], None]
    respawn: Callable[[], None]
    end: Callable[[str], None]  # (reason: str) -> None
    kicked: Callable[[str, bool], None]  # (reason: str, logged_in: bool) -> None
    error: Callable[[Exception], None]  # (error: Exception) -> None

    # Chat events
    chat: Callable[[str, str, str | None], None]  # (username, message, translate)
    whisper: Callable[[str, str], None]  # (username, message)
    message: Callable[[dict, str], None]  # (json_msg, position)

    # Game events
    game: Callable[[], None]  # Game state changed
    rain: Callable[[], None]
    time: Callable[[], None]
    health: Callable[[], None]
    breath: Callable[[], None]
    death: Callable[[], None]
    experience: Callable[[], None]

    # Entity events
    entity_spawn: Callable[[dict], None]  # (entity)
    entity_gone: Callable[[dict], None]
    entity_moved: Callable[[dict], None]
    entity_hurt: Callable[[dict, dict | None], None]  # (entity, source)
    entity_dead: Callable[[dict], None]
    entity_equip: Callable[[dict], None]
    entity_sleep: Callable[[dict], None]
    entity_wake: Callable[[dict], None]

    # Player events
    player_joined: Callable[[dict], None]  # (player)
    player_left: Callable[[dict], None]
    player_updated: Callable[[dict], None]

    # Block/World events
    block_update: Callable[[dict | None, dict], None]  # (old_block, new_block)
    chunk_column_load: Callable[[tuple], None]  # (position)
    chunk_column_unload: Callable[[tuple], None]

    # Inventory events
    window_open: Callable[[dict], None]  # (window)
    window_close: Callable[[dict], None]

    # Physics events
    move: Callable[[tuple], None]  # (position)
    forced_move: Callable[[], None]
    physics_tick: Callable[[], None]

    # Digging events
    digging_completed: Callable[[dict], None]  # (block)
    digging_aborted: Callable[[dict], None]

    # Misc events
    sleep: Callable[[], None]
    wake: Callable[[], None]
    mount: Callable[[], None]
    dismount: Callable[[dict], None]  # (vehicle)


# Event names for type-safe registration
EVENT_NAMES: set[str] = {
    "connect",
    "inject_allowed",
    "login",
    "spawn",
    "respawn",
    "end",
    "kicked",
    "error",
    "chat",
    "whisper",
    "message",
    "game",
    "rain",
    "time",
    "health",
    "breath",
    "death",
    "experience",
    "entity_spawn",
    "entity_gone",
    "entity_moved",
    "entity_hurt",
    "entity_dead",
    "entity_equip",
    "entity_sleep",
    "entity_wake",
    "player_joined",
    "player_left",
    "player_updated",
    "block_update",
    "chunk_column_load",
    "chunk_column_unload",
    "window_open",
    "window_close",
    "move",
    "forced_move",
    "physics_tick",
    "digging_completed",
    "digging_aborted",
    "sleep",
    "wake",
    "mount",
    "dismount",
}
