"""
Pyflayer - Create Minecraft bots with a powerful, high-level Python API.

A Python equivalent of mineflayer, supporting Minecraft 1.8 through 1.21.x.
"""

from __future__ import annotations

from pyflayer.bot import Bot, create_bot
from pyflayer.events import BotEvents
from pyflayer.plugin import Plugin
from pyflayer.types import BotOptions, GameState

__all__ = [
    "Bot",
    "BotEvents",
    "BotOptions",
    "GameState",
    "Plugin",
    "create_bot",
]

__version__ = "0.1.0"
