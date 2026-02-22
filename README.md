# Minepy

Create Minecraft bots with a powerful, high-level Python API.

A Python equivalent of [mineflayer](https://github.com/PrismarineJS/mineflayer), supporting Minecraft versions 1.8 through 1.21.x.

## Features

- 🤖 Async/await API with type hints
- 🔌 Plugin system with entry points
- 📦 Supports Minecraft 1.8 - 1.21.x
- 🎮 Entity tracking and management
- 🏗️ Block interaction (dig, build, place)
- 💬 Chat and commands
- 📦 Inventory management
- ⚔️ Combat and pathfinding hooks

## Installation

```bash
pip install minepy
```

## Quick Start

```python
import asyncio
from minepy import create_bot

async def main():
    bot = await create_bot(
        host="localhost",
        username="PyBot",
        auth="offline",  # or "microsoft"
    )

    @bot.on("spawn")
    async def on_spawn():
        print(f"{bot.username} spawned!")
        bot.chat("Hello from Python!")

    @bot.on("chat")
    async def on_chat(username: str, message: str):
        if username != bot.username:
            bot.chat(f"Hello {username}!")

    @bot.on("error")
    async def on_error(error: Exception):
        print(f"Error: {error}")

    await bot.wait_for("end")

asyncio.run(main())
```

## Plugin System

```python
from minepy import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"

    async def inject(self, bot: "Bot") -> None:
        @bot.on("spawn")
        async def on_spawn():
            print("Plugin loaded!")

bot.load_plugin(MyPlugin())
```

## License

MIT
