from __future__ import annotations

import asyncio
from contextlib import suppress


async def cancel_task(task: asyncio.Task, /, teardown: bool = True) -> None:
    task.cancel()

    if not teardown:
        return

    with suppress(asyncio.CancelledError):
        await task
