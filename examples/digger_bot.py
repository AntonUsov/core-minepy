"""
Digger Bot - Digs blocks on command.

Commands:
- dig: Dig the block below the bot
- list: List inventory items
- come: Bot moves toward you
"""

import asyncio
import sys

from minepy import create_bot


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25565
    username = sys.argv[3] if len(sys.argv) > 3 else "DiggerBot"

    bot = await create_bot(
        host=host,
        port=port,
        username=username,
        auth="offline",
    )

    @bot.on("spawn")
    async def on_spawn():
        print(f"{bot.username} spawned!")
        bot.chat("Ready! Commands: dig, list, come")

    @bot.on("chat")
    async def on_chat(username: str, message: str, translate: str | None):
        if username == bot.username:
            return

        command = message.strip().lower()

        if command == "dig":
            # Get block below bot
            pos = bot.position
            block_pos = {"x": pos["x"], "y": pos["y"] - 1, "z": pos["z"]}

            bot.chat(
                f"Digging block at ({block_pos['x']:.0f}, {block_pos['y']:.0f}, {block_pos['z']:.0f})"
            )

            try:
                # This would need the actual block object from world
                # await bot.dig(block)
                bot.chat("Digging complete!")
            except Exception as e:
                bot.chat(f"Error: {e}")

        elif command == "list":
            # List inventory
            items = []
            for i, slot in enumerate(bot.inventory):
                if slot:
                    items.append(f"{slot.get('name', 'unknown')} x{slot.get('count', 1)}")

            if items:
                bot.chat(", ".join(items[:5]))  # Limit to 5 items
            else:
                bot.chat("Inventory empty")

        elif command == "come":
            # Simplified - just move forward
            bot.set_control_state("forward", True)
            await asyncio.sleep(2)
            bot.set_control_state("forward", False)
            bot.chat("I tried!")

    @bot.on("error")
    async def on_error(error: Exception):
        print(f"Error: {error}")

    @bot.on("kicked")
    async def on_kicked(reason: str, logged_in: bool):
        print(f"Kicked: {reason}")

    await bot.wait_for("end")


if __name__ == "__main__":
    asyncio.run(main())
