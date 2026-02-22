"""Chat plugin - handles chat messages and commands."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from minepy.plugin import Plugin

if TYPE_CHECKING:
    from minepy.bot import Bot


class ChatPlugin(Plugin):
    """Plugin for chat functionality."""

    name = "chat"

    async def inject(self, bot: Bot) -> None:
        """Inject chat functionality into the bot."""

        # Chat patterns for parsing
        patterns: list[tuple[re.Pattern, str]] = []

        def add_chat_pattern(
            name: str, pattern: re.Pattern, repeat: bool = True
        ) -> int:
            """Add a chat pattern for parsing."""
            patterns.append((pattern, name))
            logger.debug(
                f"[ChatPlugin.add_chat_pattern] Pattern: {name}, Repeat: {repeat}"
            )
            return len(patterns) - 1

        def remove_chat_pattern(name: str | int) -> None:
            """Remove a chat pattern."""
            if isinstance(name, int):
                if 0 <= name < len(patterns):
                    patterns.pop(name)
            else:
                for i, (_, n) in enumerate(patterns):
                    if n == name:
                        patterns.pop(i)
                        break
            logger.debug(f"[ChatPlugin.remove_chat_pattern] Pattern: {name}")

        async def await_message(*filters: str | re.Pattern) -> str:
            """Wait for a message matching the filters."""
            future = bot._event_loop.create_future()

            async def handler(username: str, message: str, translate: str | None):
                for f in filters:
                    if isinstance(f, str):
                        if f not in message:
                            return
                    elif isinstance(f, re.Pattern) and not f.search(message):
                        return
                if not future.done():
                    logger.debug(
                        f"[ChatPlugin.await_message] Waiting for message matching filters: {filters}"
                    )
                    future.set_result(message)

            bot.add_event_handler("chat", handler)
            try:
                return await future
            finally:
                bot.remove_event_handler("chat", handler)

        # Add methods to bot
        bot.add_chat_pattern = add_chat_pattern
        bot.remove_chat_pattern = remove_chat_pattern
        bot.await_message = await_message

        # Enhanced chat handler with pattern matching
        @bot.on("chat")
        async def handle_chat(username: str, message: str, translate: str | None):
            for pattern, name in patterns:
                match = pattern.search(message)
                if match:
                    logger.debug(
                        f"[ChatPlugin.handle_chat] Message matched pattern '{name}': {message}"
                    )
                    await bot.emit(f"chat:{name}", username, message, match.groups())
