"""Plugin system for minepy."""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from minepy.bot import Bot

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from minepy.bot import Bot


class Plugin(ABC):
    """
    Base class for minepy plugins.

    Plugins extend bot functionality by injecting new methods and
    registering event handlers.

    Example:
        class ChatLoggerPlugin(Plugin):
            name = "chat_logger"

            async def inject(self, bot: Bot) -> None:
                @bot.on("chat")
                async def log_chat(username: str, message: str):
                    print(f"[CHAT] {username}: {message}")

        bot.load_plugin(ChatLoggerPlugin())
    """

    name: str
    """Unique identifier for this plugin."""

    dependencies: list[str] = []
    """List of plugin names that must be loaded before this one."""

    @abstractmethod
    async def inject(self, bot: Bot) -> None:
        """
        Inject plugin functionality into the bot.

        This method is called when the plugin is loaded. Override this
        to add methods to the bot and register event handlers.

        Args:
            bot: The bot instance to extend.
        """
        ...


class PluginLoader:
    """Manages plugin loading and dependency resolution."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._loaded: dict[str, Plugin] = {}
        self._loading: set[str] = set()
        logger.debug(f"[PluginLoader.__init__] Bot: {bot.username}")

    def has_plugin(self, plugin: Plugin | str) -> bool:
        """Check if a plugin is loaded."""
        name = plugin.name if isinstance(plugin, Plugin) else plugin
        return name in self._loaded

    async def load_plugin(self, plugin: Plugin) -> None:
        """
        Load a plugin into the bot.

        Args:
            plugin: Plugin instance to load.

        Raises:
            ValueError: If plugin is already loaded or dependencies missing.
        """
        if plugin.name in self._loaded:
            raise ValueError(f"Plugin '{plugin.name}' is already loaded")

        if plugin.name in self._loading:
            raise ValueError(f"Circular dependency detected for '{plugin.name}'")

        # Check dependencies
        self._loading.add(plugin.name)
        try:
            for dep in plugin.dependencies:
                if dep not in self._loaded:
                    raise ValueError(f"Plugin '{plugin.name}' requires '{dep}' which is not loaded")

            # Inject the plugin
            await plugin.inject(self._bot)
            self._loaded[plugin.name] = plugin
            logger.debug(f"[PluginLoader.load_plugin] Loaded plugin: {plugin.name}")
        finally:
            self._loading.discard(plugin.name)

    async def load_plugins(self, plugins: list[Plugin]) -> None:
        """Load multiple plugins in dependency order."""
        # Simple topological sort based on dependencies
        loaded_names: set[str] = set(self._loaded.keys())
        remaining = list(plugins)

        while remaining:
            progress = False
            for plugin in remaining[:]:
                deps_satisfied = all(dep in loaded_names for dep in plugin.dependencies)
                if deps_satisfied:
                    await self.load_plugin(plugin)
                    loaded_names.add(plugin.name)
                    remaining.remove(plugin)
                    progress = True

            if not progress and remaining:
                names = [p.name for p in remaining]
                logger.warning(f"[PluginLoader.load_plugins] Cannot resolve dependencies for: {names}")

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self._loaded.get(name)


def discover_plugins() -> dict[str, type[Plugin]]:
    """
    Discover plugins via entry points.

    Returns:
        Dict mapping plugin names to plugin classes.
    """
    import importlib.metadata as md

    plugins: dict[str, type[Plugin]] = {}

    try:
        entry_points = md.entry_points(group="minepy.plugins")
    except TypeError:
        # Python < 3.10
        entry_points = md.entry_points().get("minepy.plugins", [])

    for ep in entry_points:
        try:
            plugin_class = ep.load()
            if isinstance(plugin_class, type) and issubclass(plugin_class, Plugin):
                plugins[ep.name] = plugin_class
        except Exception:
            pass

    logger.debug(f"[discover_plugins] Found {len(plugins)} plugins")
    return plugins
