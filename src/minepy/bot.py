"""Core Bot class for minepy."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Unpack

from minepy.entity import Entity
from minepy.events import EVENT_NAMES, EventHandler
from minepy.inventory import Inventory
from minepy.plugin import Plugin, PluginLoader
from minepy.types import AuthType, BotOptions, GameState, Player, Position
from minepy.world import World

if TYPE_CHECKING:
    from minepy.protocol.connection import Connection

if TYPE_CHECKING:
    from minepy.protocol.connection import Connection

if TYPE_CHECKING:
    from minepy.protocol.connection import Connection

logger = logging.getLogger(__name__)


class Bot:
    """
    Main bot class for interacting with Minecraft servers.

    Create bots using `create_bot()` factory function.

    Example:
        bot = await create_bot(host="localhost", username="Bot", auth="offline")

        @bot.on("spawn")
        async def on_spawn():
            print(f"Spawned at {bot.position}")
            bot.chat("Hello!")

        await bot.wait_for("end")
    """

    def __init__(self, **options: Unpack[BotOptions]) -> None:
        # Connection options
        self.host: str = options.get("host", "localhost")
        self.port: int = options.get("port", 25565)
        self.username: str = options.get("username", "Player")
        self.auth: AuthType = AuthType(options.get("auth", "offline"))
        self.version: str | None = options.get("version")

        # Behavior options
        self._hide_errors: bool = options.get("hide_errors", False)
        self._log_errors: bool = options.get("log_errors", True)
        self.physics_enabled: bool = options.get("physics_enabled", True)

        # Internal state
        self._connection: Connection | None = None
        self._event_handlers: dict[str, list[EventHandler]] = {}
        self._once_handlers: dict[str, list[EventHandler]] = {}

        # Plugin system
        self._plugin_loader = PluginLoader(self)

        # Bot state
        self.position: Position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.yaw: float = 0.0
        self.pitch: float = 0.0
        self.on_ground: bool = True

        self.health: float = 20.0
        self.food: int = 20
        self.food_saturation: float = 5.0
        self.oxygen_level: int = 300

        self.game: GameState | None = None
        self.is_sleeping: bool = False
        self.is_raining: bool = False

        # World tracking
        self._world: World | None = None

                # World tracking
        self._world: World | None = None

        # Entity tracking
        self.entity: Entity | None = None
        self.entities: dict[int, Entity] = {}
        self.players: dict[str, Player] = {}
    @property
    def inventory(self) -> Inventory:
        """Get the bot's inventory."""
        if self._inventory is None:
            self._inventory = Inventory(self)
        return self._inventory

    @property
    def world(self) -> World:
        """Get the world."""
        if self._world is None:
            self._world = World()
        return self._world


        # Inventory
        self._inventory: Inventory | None = None



    # ==================== Event System ====================

    def on(self, event: str) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator to register an event handler.

        Args:
            event: Event name (e.g., "spawn", "chat", "error")

        Returns:
            Decorator function

        Example:
            @bot.on("chat")
            async def handle_chat(username: str, message: str):
                print(f"{username}: {message}")
        """
        if event not in EVENT_NAMES:
            raise ValueError(f"Unknown event: {event}")

        def decorator(handler: EventHandler) -> EventHandler:
            if event not in self._event_handlers:
                self._event_handlers[event] = []
            self._event_handlers[event].append(handler)
            return handler

        return decorator

    def once(self, event: str) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator to register a one-time event handler.

        The handler will be removed after being called once.
        """
        if event not in EVENT_NAMES:
            raise ValueError(f"Unknown event: {event}")

        def decorator(handler: EventHandler) -> EventHandler:
            if event not in self._once_handlers:
                self._once_handlers[event] = []
            self._once_handlers[event].append(handler)
            return handler

        return decorator

    def add_event_handler(self, event: str, handler: EventHandler) -> None:
        """Add an event handler without using decorator."""
        if event not in EVENT_NAMES:
            raise ValueError(f"Unknown event: {event}")
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def remove_event_handler(self, event: str, handler: EventHandler) -> bool:
        """Remove an event handler. Returns True if found and removed."""
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
                return True
            except ValueError:
                pass
        return False

    async def emit(self, event: str, *args: Any) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event: Event name
            *args: Arguments to pass to handlers
        """
        # Call persistent handlers
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                result = handler(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if not self._hide_errors:
                    logger.exception(f"Error in {event} handler: {e}")

        # Call and remove one-time handlers
        once_handlers = self._once_handlers.pop(event, [])
        for handler in once_handlers:
            try:
                result = handler(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if not self._hide_errors:
                    logger.exception(f"Error in {event} handler: {e}")

    async def wait_for(self, event: str, timeout: float | None = None) -> tuple:
        """
        Wait for an event to be emitted.

        Args:
            event: Event name to wait for
            timeout: Maximum time to wait (seconds), None for no timeout

        Returns:
            Tuple of arguments passed to the event
        """
        future: asyncio.Future[tuple] = asyncio.get_event_loop().create_future()

        async def handler(*args: Any) -> None:
            if not future.done():
                future.set_result(args)

        self.add_event_handler(event, handler)

        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            self.remove_event_handler(event, handler)

    # ==================== Plugin System ====================

    def load_plugin(self, plugin: Plugin) -> None:
        """Load a plugin into this bot."""
        return asyncio.get_event_loop().run_until_complete(
            self._plugin_loader.load_plugin(plugin)
        )

    async def load_plugin_async(self, plugin: Plugin) -> None:
        """Async version of load_plugin."""
        await self._plugin_loader.load_plugin(plugin)

    def load_plugins(self, plugins: list[Plugin]) -> None:
        """Load multiple plugins."""
        return asyncio.get_event_loop().run_until_complete(
            self._plugin_loader.load_plugins(plugins)
        )

    async def load_plugins_async(self, plugins: list[Plugin]) -> None:
        """Async version of load_plugins."""
        await self._plugin_loader.load_plugins(plugins)

    def has_plugin(self, plugin: Plugin | str) -> bool:
        """Check if a plugin is loaded."""
        return self._plugin_loader.has_plugin(plugin)

    # ==================== Core Actions ====================

    def chat(self, message: str) -> None:
        """Send a chat message."""
        if self._connection:
            self._connection.send_chat(message)

    def whisper(self, username: str, message: str) -> None:
        """Send a private message to a player."""
        self.chat(f"/msg {username} {message}")

    async def dig(self, position: Position, force_look: bool = True) -> None:
        """Dig a block at the given position."""
        # Implemented by digging plugin
        raise NotImplementedError("Load the 'digging' plugin")

    async def place_block(
        self, reference_position: Position, face: tuple[int, int, int]
    ) -> None:
        """Place a block relative to a reference block."""
        raise NotImplementedError("Load the 'place_block' plugin")

    async def equip(self, item_id: int, destination: str = "hand") -> None:
        """Equip an item to a slot."""
        raise NotImplementedError("Load the 'inventory' plugin")

    async def activate_block(self, position: Position) -> None:
        """Activate (right-click) a block."""
        if self._connection:
            await self._connection.activate_block(position)

    # ==================== Movement ====================

    def set_control_state(self, control: str, state: bool) -> None:
        """
        Set a movement control state.

        Args:
            control: One of "forward", "back", "left", "right", "jump", "sprint", "sneak"
            state: True to enable, False to disable
        """
        if self._connection:
            self._connection.set_control_state(control, state)

    def clear_control_states(self) -> None:
        """Clear all movement control states."""
        for control in ["forward", "back", "left", "right", "jump", "sprint", "sneak"]:
            self.set_control_state(control, False)

    async def look_at(self, position: Position) -> None:
        """Look at a specific position."""
        # Calculate yaw and pitch from current position to target
        dx = position["x"] - self.position["x"]
        dy = position["y"] - self.position["y"]
        dz = position["z"] - self.position["z"]

        import math

        self.yaw = math.degrees(math.atan2(-dx, dz))
        dist = math.sqrt(dx * dx + dz * dz)
        self.pitch = math.degrees(math.atan2(-dy, dist))

        if self._connection:
            await self._connection.look(self.yaw, self.pitch)

    # ==================== Connection ====================

    async def connect(self) -> None:
        """Connect to the server."""
        from minepy.protocol.connection import Connection

        self._connection = Connection(self)
        await self._connection.connect()

    def disconnect(self, reason: str = "disconnecting") -> None:
        """Disconnect from the server."""
        if self._connection:
            self._connection.disconnect(reason)
            self._connection = None

    @property
    def connected(self) -> bool:
        """Check if bot is connected to a server."""
        return self._connection is not None and self._connection.connected


async def create_bot(**options: Unpack[BotOptions]) -> Bot:
    """
    Create and connect a bot to a Minecraft server.

    Args:
        host: Server hostname or IP
        port: Server port (default: 25565)
        username: Bot username
        auth: Authentication type ("offline" or "microsoft")
        version: Minecraft version (auto-detected if not specified)

    Returns:
        Connected Bot instance

    Example:
        bot = await create_bot(
            host="localhost",
            username="MyBot",
            auth="offline",
        )
    """
    bot = Bot(**options)

    # Load internal plugins if enabled
    if options.get("load_internal_plugins", True):
        from minepy.plugin import discover_plugins

        plugins = discover_plugins()

        # Load core plugins
        for name in ["bed", "chat", "inventory", "digging"]:
            if name in plugins:
                await bot.load_plugin_async(plugins[name]())

    await bot.connect()
    return bot
