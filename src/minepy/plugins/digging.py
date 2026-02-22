"""Digging plugin - handle block breaking."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from minepy.plugin import Plugin

if TYPE_CHECKING:
    from minepy.bot import Bot


class DiggingPlugin(Plugin):
    """Plugin for digging functionality."""

    name = "digging"

    async def inject(self, bot: Bot) -> None:
        """Inject digging functionality into the bot."""

        target_dig_block: dict | None = None

        def can_dig_block(block: dict) -> bool:
            """Check if a block can be dug."""
            # Check distance (within 5 blocks)
            dx = block["position"]["x"] - bot.position["x"]
            dy = block["position"]["y"] - bot.position["y"]
            dz = block["position"]["z"] - bot.position["z"]
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5

            return distance <= 5.0 and block.get("hardness", 0) >= 0

        def dig_time(block: dict) -> float:
            """Calculate time to dig a block in seconds."""
            hardness = block.get("hardness", 1.0)

            # Simplified - doesn't account for tools
            if hardness == 0:
                return 0.0

            base_time = hardness * 1.5

            # TODO: Account for tool efficiency
            # TODO: Account for haste effect
            # TODO: Account for underwater

            return base_time

        async def dig(
            block: dict, force_look: bool = True, dig_face: str = "auto"
        ) -> None:
            """Dig a block."""
            nonlocal target_dig_block

            if target_dig_block is not None:
                raise ValueError("Already digging")

            if not can_dig_block(block):
                raise ValueError("Cannot dig this block")

            target_dig_block = block

            try:
                # Look at block if needed
                if force_look and force_look != "ignore":
                    await bot.look_at(block["position"])

                # Send dig start packet
                if bot._connection:
                    # Player Digging packet (0x1C in 1.20.4)
                    # action = 0 (start digging)
                    await bot._connection.send_dig_packet(block["position"], 0)

                # Wait for dig time (simplified - should track actual server response)
                await asyncio.sleep(dig_time(block))

                # Send dig finish packet
                if bot._connection:
                    # action = 2 (finish digging)
                    await bot._connection.send_dig_packet(block["position"], 2)

                # Wait for completion event
                await bot.wait_for("digging_completed", timeout=5.0)

            finally:
                target_dig_block = None

        def stop_digging() -> None:
            """Stop the current digging operation."""
            nonlocal target_dig_block

            if target_dig_block and bot._connection:
                # Send dig cancel packet
                # action = 1 (cancel digging)
                asyncio.create_task(
                    bot._connection.send_dig_packet(target_dig_block["position"], 1)
                )

            target_dig_block = None

        async def place_block(
            reference_block: dict, face: tuple[int, int, int]
        ) -> None:
            """Place a block."""
            # Look at reference block
            await bot.look_at(reference_block["position"])

            # Activate the block
            await bot.activate_block(reference_block["position"])

        # Add methods to bot
        bot.can_dig_block = can_dig_block
        bot.dig_time = dig_time
        bot.dig = dig
        bot.stop_digging = stop_digging
        bot.place_block = place_block
        bot.target_dig_block = None  # Will be updated dynamically

        # Update target_dig_block reference
        def update_target():
            bot.target_dig_block = target_dig_block
