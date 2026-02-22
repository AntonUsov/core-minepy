# AGENTS.md - Core-core-minepy Codebase Guide

This document provides essential information for AI coding agents working in the core-core-minepy repository.

## Project Overview

Core-core-minepy is a Python library for creating Minecraft bots (equivalent to mineflayer for Node.js), supporting Minecraft 1.8 through 1.21.x with an async/await API and full type hints.

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
pytest --cov=core-core-minepy         # Run with coverage
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
from core-core-minepy.types import BotOptions
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
src/core-core-minepy/
├── __init__.py        # Package exports
├── bot.py             # Core Bot class
├── events.py          # Event definitions
├── plugin.py          # Plugin system
├── types.py           # Type definitions
├── vec3.py            # 3D vector class
├── block.py           # Block class
├── entity.py          # Entity class
├── world.py           # World/Chunk/Section
├── protocol/
│   └── connection.py  # Network protocol
└── plugins/           # Built-in plugins
    ├── bed.py
    ├── chat.py
    ├── digging.py
    └── inventory.py
```

## Dependencies

- **anyio**: Async networking
- **pydantic**: Data validation
- **pynbt**: NBT parsing
- **cryptography**: Encryption for online auth
- **httpx**: HTTP client for Microsoft auth

## Implementation Status

### Completed
- Event system (30+ events)
- Plugin system
- Vec3, Block, Entity, World classes
- Basic protocol

### TODO
- Full packet handling
- Physics engine
- Inventory/windows
- Microsoft auth
- Combat, crafting, pathfinding

## Notes

- Type hints required on all public functions
- Use `TYPE_CHECKING` for circular imports
- Vec3 is used for all positions
