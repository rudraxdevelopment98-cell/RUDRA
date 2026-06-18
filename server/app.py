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
import hmac
import logging
import os
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
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

# --- Authentication ---------------------------------------------------------
# A login password (RUDRA_AUTH_TOKEN) gates the whole app. On success we mint a
# random session cookie kept in-memory, so restarting the server logs everyone
# out. When no token is configured, the app runs open (localhost-dev only).
SESSIONS: set[str] = set()
COOKIE_NAME = "rudra_session"
# Paths reachable without a session, so a logged-out user can actually log in.
PUBLIC_PATHS = {"/login", "/api/login", "/favicon.ico"}


def _authed(request_or_ws) -> bool:
    """True if auth is disabled, or the request carries a valid session cookie."""
    if not config.auth_token:
        return True
    return request_or_ws.cookies.get(COOKIE_NAME) in SESSIONS


LOGIN_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RUDRA — Sign in</title><style>
*{box-sizing:border-box}body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
font-family:system-ui,-apple-system,sans-serif;background:#04070d;color:#cfe9ff}
.box{width:300px;padding:30px;border:1px solid rgba(0,200,255,.25);border-radius:16px;
background:linear-gradient(155deg,rgba(12,34,56,.6),rgba(8,22,38,.6));box-shadow:0 12px 40px rgba(0,0,0,.5)}
h1{margin:0 0 4px;font-size:22px;letter-spacing:6px;color:#7df9ff}
p{margin:0 0 18px;font-size:12px;color:#6b8299;letter-spacing:1px}
input{width:100%;padding:11px 12px;border-radius:10px;border:1px solid rgba(0,200,255,.25);
background:rgba(4,11,20,.7);color:#fff;font-size:14px}
button{width:100%;margin-top:12px;padding:11px;border:none;border-radius:10px;cursor:pointer;
background:linear-gradient(135deg,#00c8ff,#0a7fcc);color:#fff;font-weight:700;letter-spacing:1px}
.err{color:#ff6b6b;font-size:12px;margin-top:10px;min-height:16px}
</style></head><body><div class="box">
<h1>RUDRA</h1><p>COMMAND CENTER</p>
<input id="pw" type="password" placeholder="Access password" autofocus>
<button id="go">Unlock</button><div class="err" id="err"></div></div><script>
const pw=document.getElementById('pw'),err=document.getElementById('err');
async function login(){err.textContent='';
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:pw.value})});
  if(r.ok){location.href='/';}else{err.textContent='Incorrect password.';pw.value='';pw.focus();}}
document.getElementById('go').onclick=login;
pw.addEventListener('keydown',e=>{if(e.key==='Enter')login();});
</script></body></html>"""


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
async def count_requests(request: Request, call_next):
    metrics.requests += 1
    # Auth gate: everything but the login surface needs a valid session.
    if request.url.path not in PUBLIC_PATHS and not _authed(request):
        if request.url.path.startswith(("/api", "/ws")):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return RedirectResponse("/login")
    return await call_next(request)


class LoginRequest(BaseModel):
    password: str


# --- Login brute-force protection -------------------------------------------
# Track failed attempts per client IP and lock that IP out after too many, so a
# public tunnel can't be hammered with password guesses.
_LOGIN_FAILS: dict[str, list[float]] = {}
_MAX_FAILS = 5            # allowed failures...
_FAIL_WINDOW = 300.0     # ...within this many seconds before lockout
_LOCKOUT = 300.0         # how long the IP stays locked out


def _client_ip(request: Request) -> str:
    # Honour the tunnel's forwarded header when present, else the socket peer.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


def _locked_out(ip: str) -> bool:
    fails = [t for t in _LOGIN_FAILS.get(ip, []) if time.monotonic() - t < _FAIL_WINDOW]
    _LOGIN_FAILS[ip] = fails
    return len(fails) >= _MAX_FAILS


def _record_fail(ip: str) -> None:
    _LOGIN_FAILS.setdefault(ip, []).append(time.monotonic())


@app.get("/login")
async def login_page() -> HTMLResponse:
    if not config.auth_token:
        return RedirectResponse("/")  # auth disabled — nothing to log into
    return HTMLResponse(LOGIN_PAGE)


@app.post("/api/login")
async def login(req: LoginRequest, request: Request) -> JSONResponse:
    ip = _client_ip(request)
    if _locked_out(ip):
        log.warning("🔒 login locked out for %s (too many attempts)", ip)
        return JSONResponse({"detail": "too many attempts — try again later"}, status_code=429)
    # Constant-time compare so a wrong password can't be timed character-by-character.
    if not config.auth_token or not hmac.compare_digest(req.password, config.auth_token):
        _record_fail(ip)
        log.warning("⚠ failed login from %s", ip)
        return JSONResponse({"detail": "invalid"}, status_code=401)
    _LOGIN_FAILS.pop(ip, None)  # clear the IP's failure history on success
    token = secrets.token_urlsafe(32)
    SESSIONS.add(token)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return resp


@app.post("/api/logout")
async def logout(request: Request) -> JSONResponse:
    SESSIONS.discard(request.cookies.get(COOKIE_NAME, ""))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


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
    if not _authed(ws):
        await ws.close(code=1008)  # policy violation
        return
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
    if not _authed(ws):
        await ws.close(code=1008)  # policy violation
        return
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
