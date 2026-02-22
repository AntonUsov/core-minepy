# AGENTS.md - Minepy Codebase Guide

This document provides essential information for AI coding agents working in the minepy repository.

## Project Overview

Minepy is a Python library for creating Minecraft bots (equivalent to mineflayer for Node.js), supporting Minecraft 1.8 through 1.21.x with an async/await API and full type hints.

## Build, Lint, and Test Commands

```bash
pip install -e ".[dev]"     # Install in dev mode
ruff check src/             # Lint
ruff check --fix src/       # Auto-fix linting issues
black src/                  # Format code
mypy src/                   # Type check
pytest                      # Run all tests
pytest tests/test_bot.py    # Specific test file
pytest -k "test_chat"       # Pattern matching
pytest tests/ -x            # Stop at first failure
```

## Code Style Guidelines

- **Line length**: 100 characters (ruff + black enforced)
- **Indentation**: 4 spaces
- **Type hints**: Required on all public functions

### Import Order
```python
from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any, Callable

# Third-party dependencies
from pydantic import BaseModel

# Internal imports
from minepy.types import BotOptions
```

### Error Handling
```python
# Validation - raise exceptions
if not valid:
    raise ValueError("Error message")

# Runtime errors - emit events
try:
    await risky_operation()
except ConnectionError as e:
    await bot.emit("error", e)
```

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions | snake_case | `async def dig_block()` |
| Classes | PascalCase | `class ChatPlugin(Plugin)` |
| Private methods | underscore prefix | `def _handle_packet()` |
| Event handlers | on_* pattern | `@bot.on("spawn")` |
| Plugins | *Plugin suffix | `class BedPlugin(Plugin)` |

## Project Structure

```
src/minepy/
├── __init__.py        # Package exports
├── bot.py             # Core Bot class
├── events.py          # Event definitions
├── plugin.py          # Plugin system
├── types.py           # Type definitions
├── protocol/          # Network protocol
├── plugins/           # Built-in plugins
└── py.typed           # PEP 561 marker

examples/              # Example bots
tests/                 # Test files
```

## Plugin Architecture

```python
from minepy.plugin import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"

    async def inject(self, bot: Bot) -> None:
        bot.my_method = self._my_method
        @bot.on("spawn")
        async def on_spawn():
            bot.chat("Plugin loaded!")

    def _my_method(self) -> str:
        return "Hello!"
```

## Testing Patterns

```python
import pytest
from minepy import Bot, create_bot

@pytest.mark.asyncio
async def test_bot_connects():
    bot = Bot(host="localhost", username="TestBot", auth="offline")
    assert bot.username == "TestBot"

@pytest.mark.asyncio
async def test_event_handler():
    bot = Bot(host="localhost", username="TestBot", auth="offline")
    received = []
    @bot.on("test")
    async def on_test(value: str):
        received.append(value)
    await bot.emit("test", "hello")
    assert received == ["hello"]
```

## Common Patterns

### Creating the Bot
```python
import asyncio
from minepy import create_bot

async def main():
    bot = await create_bot(host="localhost", username="MyBot", auth="offline")
    @bot.on("spawn")
    async def on_spawn():
        bot.chat("Hello!")
    await bot.wait_for("end")
asyncio.run(main())
```

### Event Handling
```python
@bot.on("chat")
async def on_chat(username: str, message: str, translate: str | None):
    if username != bot.username:
        bot.chat(f"Echo: {message}")
```

## Dependencies

- **anyio**: Async networking
- **pydantic**: Data validation
- **pynbt**: NBT parsing
- **cryptography**: Encryption for online auth
- **httpx**: HTTP client for Microsoft auth

## Notes

- Type hints required on all public functions
- Use `TYPE_CHECKING` for circular imports
- Raise exceptions for validation, emit events for runtime errors
- Always register error handlers (`@bot.on("error")`)
