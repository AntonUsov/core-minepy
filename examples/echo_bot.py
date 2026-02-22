"""
Echo Bot - Repeats chat messages.

This is a simple bot that echoes chat messages back to the server.
"""

import asyncio
import sys

from pyflayer import create_bot


async def main():
    # Get connection info from command line
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "EchoBot"

    # Create and connect bot
    bot = await create_bot(
        host=host,
        port=port,
        username=username,
        auth="offline",
    )

    @bot.on("spawn")
    async def on_spawn():
        print(f"{bot.username} spawned!")
        bot.chat("Hello! I will echo your messages.")

    @bot.on("chat")
    async def on_chat(username: str, message: str, translate: str | None):
        # Don't echo own messages
        if username == bot.username:
            return

        print(f"[{username}] {message}")

        # Echo the message back
        bot.chat(f"{username} said: {message}")

    @bot.on("kicked")
    async def on_kicked(reason: str, logged_in: bool):
        print(f"Kicked: {reason}")

    @bot.on("error")
    async def on_error(error: Exception):
        print(f"Error: {error}")

    @bot.on("end")
    async def on_end(reason: str):
        print(f"Disconnected: {reason}")

    # Wait forever
    await bot.wait_for("end")


if __name__ == "__main__":
    asyncio.run(main())
