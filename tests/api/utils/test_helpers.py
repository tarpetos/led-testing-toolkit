import asyncio
import pytest
import anyio

from api.utils.helpers import cancel_task


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_cancel_task_teardown():
    async def dummy_task():
        await asyncio.sleep(10)

    task = asyncio.create_task(dummy_task())
    await asyncio.sleep(0.01)  # Let the task start
    await cancel_task(task, teardown=True)
    assert task.cancelled()


@pytest.mark.anyio
async def test_cancel_task_no_teardown():
    async def dummy_task():
        await asyncio.sleep(10)

    task = asyncio.create_task(dummy_task())
    await asyncio.sleep(0.01)  # Let the task start
    await cancel_task(task, teardown=False)

    # In asyncio, a task isn't strictly done until yielded to event loop
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
