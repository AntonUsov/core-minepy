"""Inventory plugin - handle inventory management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from minepy.plugin import Plugin

if TYPE_CHECKING:
    from minepy.bot import Bot


class InventoryPlugin(Plugin):
    """Plugin for inventory functionality."""

    name = "inventory"

    async def inject(self, bot: Bot) -> None:
        """Inject inventory functionality into the bot."""

        EQUIPMENT_SLOTS = {
            "hand": 0,
            "off_hand": 1,
            "feet": 2,
            "legs": 3,
            "torso": 4,
            "head": 5,
        }

        async def equip(item_id: int, destination: str = "hand") -> None:
            """Equip an item to a slot."""
            if destination not in EQUIPMENT_SLOTS:
                raise ValueError(f"Invalid destination: {destination}")

            # Find item in inventory
            source_slot = None
            for i, slot in enumerate(bot.inventory):
                if slot and slot.get("item_id") == item_id:
                    source_slot = i
                    break

            if source_slot is None:
                raise ValueError(f"Item {item_id} not found in inventory")

            dest_slot = EQUIPMENT_SLOTS[destination]

            # Send click window packet to swap items
            # This is simplified - real implementation needs proper window handling
            if bot._connection:
                await bot._connection.click_window(source_slot, 0, 0)

        async def toss(item_id: int, count: int | None = None) -> None:
            """Drop an item from inventory."""
            for i, slot in enumerate(bot.inventory):
                if slot and slot.get("item_id") == item_id:
                    if count is None or count >= slot.get("count", 1):
                        # Drop entire stack
                        if bot._connection:
                            await bot._connection.click_window(i, 1, 0)  # Shift+click
                    else:
                        # Drop specific count
                        # Would need more complex handling
                        pass
                    break

        async def toss_stack(item: dict) -> None:
            """Drop a specific item stack."""
            slot = item.get("slot")
            if slot is not None and bot._connection:
                await bot._connection.click_window(slot, 1, 0)

        def held_item() -> dict | None:
            """Get the currently held item."""
            if bot.selected_slot < len(bot.inventory):
                return bot.inventory[bot.selected_slot]
            return None

        async def set_quick_bar_slot(slot: int) -> None:
            """Set the selected hotbar slot (0-8)."""
            if not 0 <= slot <= 8:
                raise ValueError("Slot must be 0-8")
            bot.selected_slot = slot
            if bot._connection:
                # Send held item change packet
                pass

        # Add methods to bot
        bot.equip = equip
        bot.toss = toss
        bot.toss_stack = toss_stack
        bot.held_item = held_item()
        bot.set_quick_bar_slot = set_quick_bar_slot
