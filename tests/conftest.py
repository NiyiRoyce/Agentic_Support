"""Pytest configuration for async tests."""

import pytest


# Ensure pytest-asyncio runs in auto mode for all tests
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend."""
    return "asyncio"
