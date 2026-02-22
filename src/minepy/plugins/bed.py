"""Bed plugin - handle sleep functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from minepy.plugin import Plugin

if TYPE_CHECKING:
    from minepy.bot import Bot


class BedPlugin(Plugin):
    """Plugin for bed/sleep functionality."""

    name = "bed"

    async def inject(self, bot: Bot) -> None:
        """Inject bed functionality into the bot."""

        BED_BLOCKS = {
            "white_bed",
            "orange_bed",
            "magenta_bed",
            "light_blue_bed",
            "yellow_bed",
            "lime_bed",
            "pink_bed",
            "gray_bed",
            "light_gray_bed",
            "cyan_bed",
            "purple_bed",
            "blue_bed",
            "brown_bed",
            "green_bed",
            "red_bed",
            "black_bed",
            "bed",
        }

        def is_a_bed(block: dict) -> bool:
            """Check if a block is a bed."""
            return block.get("name") in BED_BLOCKS

        async def sleep(bed_block: dict) -> None:
            """Sleep in a bed."""
            if bot.is_sleeping:
                raise ValueError("already sleeping")

            if not is_a_bed(bed_block):
                raise ValueError("not a bed block")

            # Check time (night or thunderstorm)
            time_of_day = bot.game.get("time", 0) % 24000 if bot.game else 0
            is_thunderstorm = bot.is_raining  # Simplified

            if not (12541 <= time_of_day <= 23458) and not is_thunderstorm:
                raise ValueError("it's not night and it's not a thunderstorm")

            # Activate the bed
            await bot.activate_block(bed_block["position"])

            # Wait for sleep event
            await bot.wait_for("sleep", timeout=5.0)

        async def wake() -> None:
            """Wake up from bed."""
            if not bot.is_sleeping:
                raise ValueError("already awake")

            # Send wake up packet
            if bot._connection:
                # Entity action packet (start sleeping = 2)
                pass  # Would send packet here

            await bot.wait_for("wake", timeout=5.0)

        # Add methods to bot
        bot.is_a_bed = is_a_bed
        bot.sleep = sleep
        bot.wake = wake

        # Track sleep state
        @bot.on("entity_sleep")
        async def on_entity_sleep(entity: dict):
            if entity.get("id") == bot.entity.get("id"):
                bot.is_sleeping = True
                await bot.emit("sleep")

        @bot.on("entity_wake")
        async def on_entity_wake(entity: dict):
            if entity.get("id") == bot.entity.get("id"):
                bot.is_sleeping = False
                await bot.emit("wake")
