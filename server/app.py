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
import time
from collections import deque
from contextlib import asynccontextmanager

import psutil
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


class Metrics:
    """Tracks real activity so the dashboard isn't showing fake numbers."""

    def __init__(self, maxlen: int = 120):
        self.start = time.monotonic()
        self.requests = 0
        self.chat_messages = 0
        self.errors = 0
        self.ws_connections = 0
        self.latencies_ms: deque[float] = deque(maxlen=maxlen)
        self.history: deque[dict] = deque(maxlen=maxlen)
        self.per_skill: dict[str, int] = {}

    def record_chat(self, latency_ms: float, ok: bool, skill_hint: str | None = None) -> None:
        self.chat_messages += 1
        if not ok:
            self.errors += 1
        self.latencies_ms.append(latency_ms)
        self.history.append({"t": time.time(), "latency_ms": round(latency_ms, 1), "ok": ok})
        if skill_hint:
            self.per_skill[skill_hint] = self.per_skill.get(skill_hint, 0) + 1

    def snapshot(self) -> dict:
        process = psutil.Process()
        latencies = list(self.latencies_ms)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        return {
            "uptime_s": round(time.monotonic() - self.start, 1),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "mem_percent": psutil.virtual_memory().percent,
            "process_mem_mb": round(process.memory_info().rss / (1024 * 1024), 1),
            "requests": self.requests,
            "chat_messages": self.chat_messages,
            "errors": self.errors,
            "ws_connections": self.ws_connections,
            "avg_latency_ms": round(avg_latency, 1),
            "history": list(self.history)[-40:],
            "per_skill": self.per_skill,
        }


metrics = Metrics()


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


@app.middleware("http")
async def count_requests(request, call_next):
    metrics.requests += 1
    return await call_next(request)


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    orchestrator: Orchestrator = state["orchestrator"]
    started = time.monotonic()
    try:
        reply = await orchestrator.handle(req.text)
    except Exception as exc:  # noqa: BLE001 — never let a brain error kill the request
        log.exception("chat failed")
        metrics.record_chat((time.monotonic() - started) * 1000, ok=False)
        return ChatResponse(reply=f"⚠ {exc}")
    metrics.record_chat((time.monotonic() - started) * 1000, ok=True)
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


@app.get("/api/metrics")
async def get_metrics() -> dict:
    """Real process/usage metrics for the dashboard's analytics charts."""
    return metrics.snapshot()


@app.get("/api/logs")
async def logs() -> dict:
    return {"lines": list(log_broadcaster.buffer)}


@app.get("/api/memory")
async def memory_turns() -> dict:
    """Recent conversation turns + remembered facts, for the Memory view."""
    memory: Memory = state["memory"]
    turns = await memory.recent_turns(limit=40)
    facts = await memory.all_prefs()
    return {"turns": turns, "facts": facts}


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()
    orchestrator: Orchestrator = state["orchestrator"]
    metrics.ws_connections += 1
    try:
        while True:
            text = await ws.receive_text()
            started = time.monotonic()
            try:
                reply = await orchestrator.handle(text)
            except Exception as exc:  # noqa: BLE001 — never let a brain error kill the socket
                log.exception("ws chat failed")
                reply = f"⚠ {exc}"
                metrics.record_chat((time.monotonic() - started) * 1000, ok=False)
            else:
                metrics.record_chat((time.monotonic() - started) * 1000, ok=True)
            await ws.send_json({"type": "reply", "text": reply})
    except WebSocketDisconnect:
        pass
    finally:
        metrics.ws_connections = max(0, metrics.ws_connections - 1)


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
