"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def bot_options():
    """Default bot options for testing."""
    return {
        "host": "localhost",
        "port": 25565,
        "username": "TestBot",
        "auth": "offline",
    }
