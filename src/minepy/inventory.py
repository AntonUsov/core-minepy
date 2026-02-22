"""Inventory and window management for minepy."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from minepy.entity import Item

if TYPE_CHECKING:
    from minepy.bot import Bot

logger = logging.getLogger(__name__)


class WindowType(str, Enum):
    """Window types."""

    INVENTORY = "inventory"
    CHEST = "chest"
    CRAFTING_TABLE = "crafting_table"
    FURNACE = "furnace"
    BLAST_FURNACE = "blast_furnace"
    SMOKER = "smoker"
    ANVIL = "anvil"
    ENCHANTMENT_TABLE = "enchantment_table"
    BREWING_STAND = "brewing_stand"
    HOPPER = "hopper"
    DISPENSER = "dispenser"
    DROPPER = "dropper"
    SHULKER_BOX = "shulker_box"
    BARREL = "barrel"
    VILLAGER = "villager"
    BEACON = "beacon"
    LOOM = "loom"
    CARTOGRAPHY_TABLE = "cartography_table"
    GRINDSTONE = "grindstone"
    STONECUTTER = "stonecutter"
    SMITHING_TABLE = "smithing_table"
    LECTERN = "lectern"
    CREATIVE = "creative"


@dataclass
class Slot:
    """A single inventory slot."""

    index: int
    item: Item | None = None

    @property
    def is_empty(self) -> bool:
        return self.item is None or self.item.count <= 0

    @classmethod
    def from_dict(cls, data: dict) -> Slot:
        return cls(
            index=data.get("index", 0),
            item=Item.from_dict(data["item"]) if data.get("item") else None,
        )


@dataclass
class Window:
    """
    Represents an open window (inventory, chest, etc.).

    Attributes:
        id: Window ID from server
        type: Window type
        title: Window title (JSON component)
        slots: All slots in this window
        inventory_start: Index where player inventory starts
    """

    id: int
    type: WindowType = WindowType.INVENTORY
    title: str = ""
    slots: list[Slot] = field(default_factory=list)
    inventory_start: int = 0

    # Selected slot (cursor item)
    selected_slot: int = -1
    cursor_item: Item | None = None

    # For crafting windows
    crafting_result: Slot | None = None
    crafting_grid: list[Slot] = field(default_factory=list)

    @property
    def slot_count(self) -> int:
        return len(self.slots)

    def get_slot(self, index: int) -> Slot | None:
        """Get slot by index."""
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def set_slot(self, index: int, item: Item | None) -> None:
        """Set item in slot."""
        if 0 <= index < len(self.slots):
            self.slots[index].item = item

    def get_container_slots(self) -> list[Slot]:
        """Get only container slots (not player inventory)."""
        if self.inventory_start > 0:
            return self.slots[: self.inventory_start]
        return self.slots

    def get_inventory_slots(self) -> list[Slot]:
        """Get player inventory slots within this window."""
        if self.inventory_start > 0:
            return self.slots[self.inventory_start :]
        return []

    def find_item(self, item_id: int, metadata: int | None = None) -> list[Slot]:
        """Find all slots containing an item."""
        result = []
        for slot in self.slots:
            if (slot.item and slot.item.id == item_id and (metadata is None or slot.item.metadata == metadata)):
                result.append(slot)
        return result

    def find_empty_slot(self, start: int = 0) -> Slot | None:
        """Find first empty slot starting from index."""
        for i in range(start, len(self.slots)):
            if self.slots[i].is_empty:
                return self.slots[i]
        return None


class Inventory:
    """
    Manages the player's inventory.

    Slot layout (standard 46-slot inventory):
    - 0-8: Hotbar
    - 9-35: Main inventory (3 rows of 9)
    - 36: Boots
    - 37: Leggings
    - 38: Chestplate
    - 39: Helmet
    - 40: Off-hand
    - 45: Crafting result (if crafting window open)
    """

    SLOT_HOTBAR_START = 0
    SLOT_HOTBAR_END = 8
    SLOT_INVENTORY_START = 9
    SLOT_INVENTORY_END = 35
    SLOT_BOOTS = 36
    SLOT_LEGGINGS = 37
    SLOT_CHESTPLATE = 38
    SLOT_HELMET = 39
    SLOT_OFFHAND = 40

    EQUIPMENT_SLOTS = {
        "hand": 0,  # Main hand (actually selected hotbar slot)
        "off-hand": 40,
        "feet": 36,
        "legs": 37,
        "torso": 38,
        "head": 39,
    }

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

        # Current window (None = player inventory)
        self._current_window: Window | None = None

        # Player inventory (always accessible)
        self._slots: list[Slot] = [Slot(i) for i in range(46)]

        # Selected hotbar slot
        self._selected_slot: int = 0

        # Cursor item (item being moved)
        self._cursor_item: Item | None = None

    @property
    def selected_slot(self) -> int:
        return self._selected_slot

    @selected_slot.setter
    def selected_slot(self, value: int) -> None:
        self._selected_slot = max(0, min(8, value))

    @property
    def current_window(self) -> Window | None:
        return self._current_window

    @property
    def cursor_item(self) -> Item | None:
        return self._cursor_item

    # ==================== Slot Access ====================

    def get_slot(self, index: int) -> Slot | None:
        """Get inventory slot by index."""
        if 0 <= index < len(self._slots):
            return self._slots[index]
        return None

    def set_slot(self, index: int, item: Item | None) -> None:
        """Set item in inventory slot."""
        if 0 <= index < len(self._slots):
            self._slots[index].item = item

    def get_hotbar_slot(self, index: int) -> Slot | None:
        """Get hotbar slot (0-8)."""
        return self.get_slot(index)

    def get_held_item(self) -> Item | None:
        """Get item in currently selected hotbar slot."""
        slot = self.get_slot(self._selected_slot)
        return slot.item if slot else None

    # ==================== Item Finding ====================

    def find_item(self, item_id: int, metadata: int | None = None) -> list[Slot]:
        """Find all slots containing an item."""
        result = []
        for slot in self._slots:
            if slot.item and slot.item.id == item_id:
                if metadata is None or slot.item.metadata == metadata:
                    result.append(slot)
        return result

    def find_item_by_name(self, name: str) -> list[Slot]:
        """Find all slots containing an item by name."""
        result = []
        for slot in self._slots:
            if slot.item and slot.item.name == name:
                result.append(slot)
        return result

    def count_item(self, item_id: int, metadata: int | None = None) -> int:
        """Count total items of a type."""
        total = 0
        for slot in self.find_item(item_id, metadata):
            if slot.item:
                total += slot.item.count
        return total

    def has_item(self, item_id: int, count: int = 1, metadata: int | None = None) -> bool:
        """Check if inventory has at least count of an item."""
        return self.count_item(item_id, metadata) >= count

    def find_empty_slot(self, prefer_hotbar: bool = False) -> Slot | None:
        """Find an empty slot."""
        if prefer_hotbar:
            for i in range(9):
                if self._slots[i].is_empty:
                    return self._slots[i]

        for i in range(9, 36):
            if self._slots[i].is_empty:
                return self._slots[i]

        return None

    # ==================== Equipment ====================

    def get_equipment(self, slot_name: str) -> Item | None:
        """Get equipment by slot name (head, torso, legs, feet, off-hand)."""
        slot_index = self.EQUIPMENT_SLOTS.get(slot_name)
        if slot_index is not None:
            slot = self.get_slot(slot_index)
            return slot.item if slot else None
        return None

    def get_helmet(self) -> Item | None:
        return self.get_equipment("head")

    def get_chestplate(self) -> Item | None:
        return self.get_equipment("torso")

    def get_leggings(self) -> Item | None:
        return self.get_equipment("legs")

    def get_boots(self) -> Item | None:
        return self.get_equipment("feet")

    def get_offhand(self) -> Item | None:
        return self.get_equipment("off-hand")

    # ==================== Window Management ====================

    def open_window(self, window: Window) -> None:
        """Handle window open event."""
        self._current_window = window
        logger.debug(f"Opened window {window.id} ({window.type})")

    def close_window(self) -> None:
        """Handle window close event."""
        self._current_window = None
        self._cursor_item = None
        logger.debug("Closed window")

    def update_slot(self, window_id: int, slot_index: int, item: Item | None) -> None:
        """Update a slot in the current window or inventory."""
        if window_id == 0:  # Player inventory
            self.set_slot(slot_index, item)
        elif self._current_window and self._current_window.id == window_id:
            self._current_window.set_slot(slot_index, item)

    def update_window_items(self, window_id: int, items: list[Item | None]) -> None:
        """Update all items in a window."""
        if window_id == 0:  # Player inventory
            for i, item in enumerate(items):
                if i < len(self._slots):
                    self._slots[i].item = item
        elif self._current_window and self._current_window.id == window_id:
            for i, item in enumerate(items):
                if i < len(self._current_window.slots):
                    self._current_window.slots[i].item = item

    # ==================== Actions ====================

    async def set_quick_bar_slot(self, slot: int) -> None:
        """Set the selected hotbar slot."""
        if not 0 <= slot <= 8:
            raise ValueError("Slot must be 0-8")

        self._selected_slot = slot

        if self._bot._connection:
            await self._bot._connection.send_held_item_change(slot)

    async def equip(self, item: Item | int, destination: str = "hand") -> None:
        """
        Equip an item to a destination.

        Args:
            item: Item or item ID to equip
            destination: hand, off-hand, head, torso, legs, feet
        """
        if destination not in self.EQUIPMENT_SLOTS:
            raise ValueError(f"Invalid destination: {destination}")

        item_id = item.id if isinstance(item, Item) else item

        # Find item in inventory
        source_slots = self.find_item(item_id)
        if not source_slots:
            raise ValueError(f"Item {item_id} not found in inventory")

        source_slot = source_slots[0]

        # Use connection to perform click
        if self._bot._connection:
            dest_index = self.EQUIPMENT_SLOTS[destination]

            # Shift-click to equip
            await self._bot._connection.send_click_window(
                window_id=0,
                slot=source_slot.index,
                button=0,
                mode=1,  # Shift-click
                item=source_slot.item,
            )

    async def toss(self, item: Item | int, count: int = 1) -> None:
        """
        Drop an item from inventory.

        Args:
            item: Item or item ID to drop
            count: Number to drop (None = all)
        """
        item_id = item.id if isinstance(item, Item) else item

        slots = self.find_item(item_id)
        if not slots:
            raise ValueError(f"Item {item_id} not found in inventory")

        slot = slots[0]
        if slot.item is None:
            return

        if count is None or count >= slot.item.count:
            # Drop entire stack (click outside window)
            if self._bot._connection:
                await self._bot._connection.send_click_window(
                    window_id=0,
                    slot=slot.index,
                    button=0,
                    mode=4,  # Drop item
                    item=slot.item,
                )
        else:
            # Drop specific count (right-click outside window)
            # This requires picking up and dropping
            pass

    async def toss_stack(self, slot: Slot) -> None:
        """Drop entire stack from a slot."""
        if slot.item is None:
            return

        if self._bot._connection:
            await self._bot._connection.send_click_window(
                window_id=0,
                slot=slot.index,
                button=1,  # Control key (drop entire stack)
                mode=4,  # Drop item
                item=slot.item,
            )

    # ==================== Container Actions ====================

    async def deposit(
        self,
        item_id: int,
        metadata: int | None = None,
        count: int = 1,
    ) -> None:
        """
        Deposit items into the currently open container.

        Args:
            item_id: Item ID to deposit
            metadata: Item metadata (None = any)
            count: Number to deposit
        """
        if not self._current_window:
            raise ValueError("No container open")

        slots = self.find_item(item_id, metadata)
        remaining = count

        for slot in slots:
            if remaining <= 0:
                break

            if slot.item is None:
                continue

            # Shift-click to move to container
            if self._bot._connection:
                await self._bot._connection.send_click_window(
                    window_id=self._current_window.id,
                    slot=slot.index,
                    button=0,
                    mode=1,  # Shift-click
                    item=slot.item,
                )
                remaining -= slot.item.count

    async def withdraw(
        self,
        item_id: int,
        metadata: int | None = None,
        count: int = 1,
    ) -> None:
        """
        Withdraw items from the currently open container.

        Args:
            item_id: Item ID to withdraw
            metadata: Item metadata (None = any)
            count: Number to withdraw
        """
        if not self._current_window:
            raise ValueError("No container open")

        container_slots = self._current_window.get_container_slots()
        remaining = count

        for slot in container_slots:
            if remaining <= 0:
                break

            if slot.is_empty or slot.item is None:
                continue

            if slot.item.id != item_id:
                continue

            if metadata is not None and slot.item.metadata != metadata:
                continue

            # Shift-click to move to inventory
            if self._bot._connection:
                await self._bot._connection.send_click_window(
                    window_id=self._current_window.id,
                    slot=slot.index,
                    button=0,
                    mode=1,  # Shift-click
                    item=slot.item,
                )
                remaining -= slot.item.count

    async def close(self) -> None:
        """Close the currently open window."""
        if self._current_window and self._bot._connection:
            await self._bot._connection.send_close_window(self._current_window.id)
            self.close_window()

    # ==================== Utility ====================

    def get_inventory_summary(self) -> dict[str, Any]:
        """Get a summary of inventory contents."""
        summary = {
            "selected_slot": self._selected_slot,
            "held_item": self.get_held_item(),
            "equipment": {
                "helmet": self.get_helmet(),
                "chestplate": self.get_chestplate(),
                "leggings": self.get_leggings(),
                "boots": self.get_boots(),
                "offhand": self.get_offhand(),
            },
            "item_counts": {},
        }

        # Count items
        for slot in self._slots:
            if slot.item:
                name = slot.item.name or str(slot.item.id)
                if name not in summary["item_counts"]:
                    summary["item_counts"][name] = 0
                summary["item_counts"][name] += slot.item.count

        return summary

    def __repr__(self) -> str:
        window = f", window={self._current_window.type}" if self._current_window else ""
        return f"Inventory(selected={self._selected_slot}{window})"
