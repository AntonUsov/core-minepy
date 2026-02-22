"""
Guard Bot - Attacks hostile mobs near a position.

This bot will attack any hostile mob that comes within range
of its guard position.
"""

import asyncio
import sys

from minepy import create_bot


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "GuardBot"

    bot = await create_bot(
        host=host,
        port=port,
        username=username,
        auth="offline",
    )

    guard_pos = None
    guard_range = 10

    @bot.on("spawn")
    async def on_spawn():
        nonlocal guard_pos
        guard_pos = bot.position.copy()
        print(f"{bot.username} spawned! Guarding position.")
        bot.chat(f"Guarding position at spawn!")

    @bot.on("chat")
    async def on_chat(username: str, message: str, translate: str | None):
        if username == bot.username:
            return

        if message.strip().lower() == "follow":
            nonlocal guard_pos
            guard_pos = bot.position.copy()
            bot.chat("Now following!")

    @bot.on("entity_spawn")
    async def on_entity_spawn(entity: dict):
        # Check if entity is hostile
        if entity.get("kind") == "Hostile mobs":
            # Check distance to guard position
            if guard_pos:
                dx = entity["position"]["x"] - guard_pos["x"]
                dy = entity["position"]["y"] - guard_pos["y"]
                dz = entity["position"]["z"] - guard_pos["z"]
                distance = (dx * dx + dy * dy + dz * dz) ** 0.5

                if distance <= guard_range:
                    bot.chat(f"Hostile detected: {entity.get('name', 'unknown')}")
                    # Attack logic would go here
                    # bot.attack(entity)

    @bot.on("error")
    async def on_error(error: Exception):
        print(f"Error: {error}")

    @bot.on("kicked")
    async def on_kicked(reason: str, logged_in: bool):
        print(f"Kicked: {reason}")

    await bot.wait_for("end")


if __name__ == "__main__":
    asyncio.run(main())
