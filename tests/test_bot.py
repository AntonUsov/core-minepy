"""Tests for the core Bot class."""

import pytest

from pyflayer import Bot, create_bot
from pyflayer.plugin import Plugin


class TestBotCreation:
    """Tests for bot creation."""

    def test_bot_default_options(self):
        """Bot should have default options."""
        bot = Bot()
        assert bot.host == "localhost"
        assert bot.port == 25565
        assert bot.username == "Player"
        assert bot.auth.value == "offline"

    def test_bot_custom_options(self):
        """Bot should accept custom options."""
        bot = Bot(
            host="example.com",
            port=25566,
            username="CustomBot",
            auth="microsoft",
        )
        assert bot.host == "example.com"
        assert bot.port == 25566
        assert bot.username == "CustomBot"
        assert bot.auth.value == "microsoft"


class TestEventSystem:
    """Tests for the event system."""

    @pytest.mark.asyncio
    async def test_on_decorator(self):
        """on() decorator should register handler."""
        bot = Bot()
        called = []

        @bot.on("spawn")
        async def on_spawn():
            called.append(True)

        await bot.emit("spawn")
        assert called == [True]

    @pytest.mark.asyncio
    async def test_once_decorator(self):
        """once() decorator should fire only once."""
        bot = Bot()
        called = []

        @bot.once("spawn")
        async def on_spawn():
            called.append(True)

        await bot.emit("spawn")
        await bot.emit("spawn")
        assert called == [True]

    @pytest.mark.asyncio
    async def test_emit_with_args(self):
        """emit() should pass arguments to handlers."""
        bot = Bot()
        received = []

        @bot.on("chat")
        async def on_chat(username: str, message: str, translate):
            received.append((username, message))

        await bot.emit("chat", "Player1", "Hello", None)
        assert received == [("Player1", "Hello")]

    @pytest.mark.asyncio
    async def test_wait_for_event(self):
        """wait_for() should return event args."""
        bot = Bot()

        # Emit event after a delay (using valid event name)
        async def emit_later():
            import asyncio

            await asyncio.sleep(0.1)
            await bot.emit("spawn")

        import asyncio

        asyncio.create_task(emit_later())

        result = await bot.wait_for("spawn", timeout=1.0)
        assert result == ()

    def test_invalid_event_raises(self):
        """Invalid event name should raise ValueError."""
        bot = Bot()

        with pytest.raises(ValueError):

            @bot.on("invalid_event")
            async def handler():
                pass


class TestPluginSystem:
    """Tests for the plugin system."""

    @pytest.mark.asyncio
    async def test_load_plugin(self):
        """Plugin should be loaded and inject method called."""
        bot = Bot()
        injected = []

        class TestPlugin(Plugin):
            name = "test"

            async def inject(self, bot: Bot) -> None:
                injected.append(True)

        await bot.load_plugin_async(TestPlugin())
        assert injected == [True]
        assert bot.has_plugin("test")

    @pytest.mark.asyncio
    async def test_plugin_dependencies(self):
        """Plugin with missing dependency should raise error."""
        bot = Bot()

        class DependentPlugin(Plugin):
            name = "dependent"
            dependencies = ["missing"]

            async def inject(self, bot: Bot) -> None:
                pass

        with pytest.raises(ValueError):
            await bot.load_plugin_async(DependentPlugin())
