"""
RUDRA web server — a graphical front end for the brain.

Boots the same subsystems as `core.main` (memory, bus, skills, orchestrator)
but exposes them over HTTP/WebSocket instead of (or alongside) the terminal,
so the dashboard in `dashboard/` can chat with RUDRA and watch it work from a
browser.

Run locally:
    pip install -r requirements.txt
    uvicorn server.app:app --host 0.0.0.0 --port 8080

Then open http://localhost:8080
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.brain.orchestrator import Orchestrator
from core.bus.mqtt import Bus
from core.config import config
from core.log import get_logger
from core.memory.store import Memory
from core.skills import load_skills

log = get_logger("rudra.server")

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard")

state: dict = {}


class LogBroadcaster(logging.Handler):
    """Tees every log line into a ring buffer + any connected WebSocket."""

    def __init__(self, maxlen: int = 200):
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=maxlen)
        self.sockets: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        self.buffer.append(line)
        if self.loop is None or not self.sockets:
            return
        for ws in list(self.sockets):
            asyncio.run_coroutine_threadsafe(self._send(ws, line), self.loop)

    async def _send(self, ws: WebSocket, line: str) -> None:
        try:
            await ws.send_json({"type": "log", "line": line})
        except Exception:  # noqa: BLE001 — a dead socket shouldn't break logging
            self.sockets.discard(ws)


log_broadcaster = LogBroadcaster()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_broadcaster.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)-18s  %(message)s", datefmt="%H:%M:%S"))
    log_broadcaster.loop = asyncio.get_event_loop()
    logging.getLogger().addHandler(log_broadcaster)

    for warning in config.validate():
        log.warning("⚠ %s", warning)

    memory = Memory(config.db_path)
    await memory.init()
    bus = Bus(config)
    await bus.connect()
    skills = load_skills(bus, memory)
    orchestrator = Orchestrator(config, bus, memory, skills)

    state["memory"] = memory
    state["bus"] = bus
    state["skills"] = skills
    state["orchestrator"] = orchestrator
    log.info("🌐 web server ready — %d skills loaded", len(skills))

    yield

    await bus.disconnect()
    await memory.close()
    logging.getLogger().removeHandler(log_broadcaster)


app = FastAPI(title="RUDRA", lifespan=lifespan)


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    orchestrator: Orchestrator = state["orchestrator"]
    try:
        reply = await orchestrator.handle(req.text)
    except Exception as exc:  # noqa: BLE001 — never let a brain error kill the request
        log.exception("chat failed")
        return ChatResponse(reply=f"⚠ {exc}")
    return ChatResponse(reply=reply)


@app.get("/api/status")
async def status() -> dict:
    memory: Memory = state["memory"]
    skills = state["skills"]
    devices = await memory.online_devices()
    capabilities = [
        {"name": t["name"], "description": t["description"]}
        for skill in skills.values()
        for t in skill.tools()
    ]
    return {
        "name": config.name,
        "skills": sorted(skills.keys()),
        "devices": devices,
        "capabilities": capabilities,
        "voice_enabled": config.voice_enabled,
    }


@app.get("/api/logs")
async def logs() -> dict:
    return {"lines": list(log_broadcaster.buffer)}


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()
    orchestrator: Orchestrator = state["orchestrator"]
    try:
        while True:
            text = await ws.receive_text()
            try:
                reply = await orchestrator.handle(text)
            except Exception as exc:  # noqa: BLE001 — never let a brain error kill the socket
                log.exception("ws chat failed")
                reply = f"⚠ {exc}"
            await ws.send_json({"type": "reply", "text": reply})
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket) -> None:
    await ws.accept()
    log_broadcaster.sockets.add(ws)
    try:
        for line in list(log_broadcaster.buffer)[-50:]:
            await ws.send_json({"type": "log", "line": line})
        while True:
            await ws.receive_text()  # keep the connection open; client sends nothing meaningful
    except WebSocketDisconnect:
        pass
    finally:
        log_broadcaster.sockets.discard(ws)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(os.path.join(DASHBOARD_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")
