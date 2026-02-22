"""Tests for the plugin system."""

import pytest

from minepy.bot import Bot
from minepy.plugin import Plugin, PluginLoader


class MockPlugin(Plugin):
    """Mock plugin for testing."""

    name = "mock"

    def __init__(self):
        self.injected = False
        self.bot = None

    async def inject(self, bot: Bot) -> None:
        self.injected = True
        self.bot = bot


class TestPluginLoader:
    """Tests for PluginLoader."""

    def test_has_plugin(self):
        """has_plugin() should return correct status."""
        bot = Bot()
        loader = PluginLoader(bot)
        plugin = MockPlugin()

        assert not loader.has_plugin(plugin)
        assert not loader.has_plugin("mock")

    @pytest.mark.asyncio
    async def test_load_plugin(self):
        """load_plugin() should call inject()."""
        bot = Bot()
        loader = PluginLoader(bot)
        plugin = MockPlugin()

        await loader.load_plugin(plugin)

        assert plugin.injected
        assert plugin.bot is bot
        assert loader.has_plugin("mock")

    @pytest.mark.asyncio
    async def test_load_plugin_twice_raises(self):
        """Loading same plugin twice should raise error."""
        bot = Bot()
        loader = PluginLoader(bot)
        plugin = MockPlugin()

        await loader.load_plugin(plugin)

        with pytest.raises(ValueError):
            await loader.load_plugin(plugin)

    @pytest.mark.asyncio
    async def test_load_plugins_in_order(self):
        """load_plugins() should respect dependencies."""
        bot = Bot()
        loader = PluginLoader(bot)

        load_order = []

        class PluginA(Plugin):
            name = "a"

            async def inject(self, bot):
                load_order.append("a")

        class PluginB(Plugin):
            name = "b"
            dependencies = ["a"]

            async def inject(self, bot):
                load_order.append("b")

        await loader.load_plugins([PluginB(), PluginA()])

        assert load_order == ["a", "b"]
