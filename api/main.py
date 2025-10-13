import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from api.core.config import API_HOST, API_PORT
from api.endpoints import devices, log_parser, player, tools, websocket
from api.services.player_service import player_service
from api.utils.helpers import cancel_task


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    player_task = asyncio.create_task(player_service.playback_loop())
    broadcast_task = asyncio.create_task(websocket.broadcast_loop())

    yield

    await cancel_task(player_task)
    await cancel_task(broadcast_task)


app = FastAPI(title="LED Testing Toolkit API", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(devices.router, prefix="/api/v1")
app.include_router(player.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(log_parser.router, prefix="/api/v1")
app.include_router(tools.router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
