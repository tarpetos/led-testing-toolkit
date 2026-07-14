"""
Helper functions for the API.

This module provides utility functions used across the API,
such as task cancellation helpers.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress


async def cancel_task(task: asyncio.Task, /, teardown: bool = True) -> None:
    """
    Cancel an asyncio task and optionally wait for its teardown.

    Args:
        task: The asyncio task to cancel.
        teardown: Whether to await the task to ensure it has fully shut down
            after being cancelled. Defaults to True.

    """
    task.cancel()

    if not teardown:
        return

    with suppress(asyncio.CancelledError):
        await task
