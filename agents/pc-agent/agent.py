"""
RUDRA PC Agent.

Runs on the computer you want to control. It:
  1. connects to the MQTT bus,
  2. announces itself (register) with its capabilities,
  3. listens on  rudra/pc/<this-pc>/cmd  and executes allow-listed actions,
  4. reports the result on the command's reply_to topic (an Event).

Security:
  - only apps/scripts in ALLOW_LIST may run,
  - power actions (lock/sleep/shutdown) are refused unless the command carries
    "confirmed": true (the brain asks the user first — see docs/PROTOCOL.md).

Run:
    pip install -r requirements.txt
    export MQTT_HOST=...        # default localhost
    export RUDRA_PC_ID=main-pc  # this machine's id
    python agent.py
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import subprocess
import time
import uuid

DEVICE_ID = os.environ.get("RUDRA_PC_ID", "main-pc")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME") or None
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD") or None
MQTT_TLS = os.environ.get("MQTT_TLS", "").lower() == "true"

OS = platform.system()  # 'Linux' | 'Darwin' | 'Windows'

CMD_TOPIC = f"rudra/pc/{DEVICE_ID}/cmd"
REGISTER_TOPIC = "rudra/system/all/register"

CAPABILITIES = ["pc.open_app", "pc.run_script", "pc.volume", "pc.power", "pc.search_files"]

# Only these may be launched/run. Edit to taste.
# apps: spoken name → command to launch.
ALLOW_LIST_APPS = {
    "code": "code",
    "chrome": "google-chrome",
    "firefox": "firefox",
    "spotify": "spotify",
    "terminal": {"Linux": "x-terminal-emulator", "Darwin": "Terminal", "Windows": "cmd"},
}
# scripts: name → argv list (no shell). Add your own here.
ALLOW_LIST_SCRIPTS: dict[str, list[str]] = {}

# Where pc.search_files looks.
SEARCH_ROOT = os.path.expanduser(os.environ.get("RUDRA_SEARCH_ROOT", "~"))


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def register_payload() -> dict:
    return {
        "device": DEVICE_ID,
        "domain": "pc",
        "capabilities": CAPABILITIES,
        "meta": {"os": OS.lower(), "agent": "0.1.0"},
    }


def ok(result: dict) -> dict:
    return {"ok": True, "result": result, "error": None}


def err(message: str) -> dict:
    return {"ok": False, "result": None, "error": message}


# --- action handlers ----------------------------------------------------------

def do_open_app(args: dict) -> dict:
    app = (args.get("app") or "").lower()
    if app not in ALLOW_LIST_APPS:
        return err(f"app '{app}' is not allow-listed")
    cmd = ALLOW_LIST_APPS[app]
    if isinstance(cmd, dict):
        cmd = cmd.get(OS, app)
    try:
        if OS == "Darwin":
            subprocess.Popen(["open", "-a", cmd])
        elif OS == "Windows":
            os.startfile(cmd)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([cmd])
        return ok({"opened": app})
    except Exception as exc:  # noqa: BLE001
        return err(f"could not open {app}: {exc}")


def do_run_script(args: dict) -> dict:
    name = args.get("name")
    if name not in ALLOW_LIST_SCRIPTS:
        return err(f"script '{name}' is not allow-listed")
    argv = ALLOW_LIST_SCRIPTS[name] + list(args.get("args") or [])
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        return ok({"script": name, "code": proc.returncode,
                   "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]})
    except Exception as exc:  # noqa: BLE001
        return err(f"script '{name}' failed: {exc}")


def do_volume(args: dict) -> dict:
    level = int(args.get("level", 50))
    try:
        if OS == "Darwin":
            if level < 0:
                subprocess.run(["osascript", "-e", "set volume with output muted"])
            else:
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
        elif OS == "Linux":
            if shutil.which("pactl"):
                if level < 0:
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
                else:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
            elif shutil.which("amixer"):
                target = "mute" if level < 0 else f"{level}%"
                subprocess.run(["amixer", "set", "Master", target])
            else:
                return err("no volume tool (pactl/amixer) found")
        else:  # Windows — needs pycaw (optional dependency)
            try:
                from ctypes import POINTER, cast
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                speakers = AudioUtilities.GetSpeakers()
                iface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol = cast(iface, POINTER(IAudioEndpointVolume))
                if level < 0:
                    vol.SetMute(1, None)
                else:
                    vol.SetMute(0, None)
                    vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            except ImportError:
                return err("install pycaw for Windows volume control")
        return ok({"volume": "muted" if level < 0 else level})
    except Exception as exc:  # noqa: BLE001
        return err(f"volume change failed: {exc}")


def do_power(args: dict, confirmed: bool) -> dict:
    mode = args.get("mode", "lock")
    if not confirmed:
        return err("power actions require confirmation (confirmed: true)")
    cmds = {
        "Linux": {
            "lock": ["loginctl", "lock-session"],
            "sleep": ["systemctl", "suspend"],
            "shutdown": ["shutdown", "-h", "now"],
        },
        "Darwin": {
            "lock": ["pmset", "displaysleepnow"],
            "sleep": ["pmset", "sleepnow"],
            "shutdown": ["osascript", "-e", 'tell app "System Events" to shut down'],
        },
        "Windows": {
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "shutdown": ["shutdown", "/s", "/t", "0"],
        },
    }
    argv = cmds.get(OS, {}).get(mode)
    if not argv:
        return err(f"power mode '{mode}' not supported on {OS}")
    try:
        subprocess.Popen(argv)
        return ok({"power": mode})
    except Exception as exc:  # noqa: BLE001
        return err(f"power {mode} failed: {exc}")


def do_search_files(args: dict) -> dict:
    query = (args.get("query") or "").lower()
    if not query:
        return err("empty query")
    matches: list[str] = []
    for root, _dirs, files in os.walk(SEARCH_ROOT):
        if any(part.startswith(".") for part in root.split(os.sep)):
            continue  # skip hidden/system dirs
        for f in files:
            if query in f.lower():
                matches.append(os.path.join(root, f))
                if len(matches) >= 20:
                    return ok({"query": query, "matches": matches, "truncated": True})
    return ok({"query": query, "matches": matches, "truncated": False})


HANDLERS = {
    "pc.open_app": lambda a, c: do_open_app(a),
    "pc.run_script": lambda a, c: do_run_script(a),
    "pc.volume": lambda a, c: do_volume(a),
    "pc.power": lambda a, c: do_power(a, c),
    "pc.search_files": lambda a, c: do_search_files(a),
}


def handle_command(cmd: dict) -> dict:
    """Execute one command, return an Event dict."""
    action = cmd.get("action")
    args = cmd.get("args") or {}
    confirmed = bool(cmd.get("confirmed"))
    handler = HANDLERS.get(action)
    if not handler:
        event = err(f"unknown action: {action}")
    else:
        try:
            event = handler(args, confirmed)
        except Exception as exc:  # noqa: BLE001
            event = err(f"{action} crashed: {exc}")
    event.update({"id": new_id("evt"), "ts": int(time.time()), "in_reply_to": cmd.get("id")})
    return event


async def main() -> None:
    import aiomqtt

    print(f"[pc-agent] {DEVICE_ID} on {OS} — connecting to {MQTT_HOST}:{MQTT_PORT}"
          f"{' (TLS)' if MQTT_TLS else ''}")
    tls_params = aiomqtt.TLSParameters() if MQTT_TLS else None
    async with aiomqtt.Client(
        hostname=MQTT_HOST, port=MQTT_PORT,
        username=MQTT_USERNAME, password=MQTT_PASSWORD,
        tls_params=tls_params,
    ) as client:
        await client.publish(REGISTER_TOPIC, json.dumps(register_payload()))
        await client.subscribe(CMD_TOPIC)
        print(f"[pc-agent] online. capabilities: {', '.join(CAPABILITIES)}")
        async for message in client.messages:
            try:
                cmd = json.loads(message.payload)
            except (json.JSONDecodeError, TypeError):
                continue
            event = handle_command(cmd)
            reply_to = cmd.get("reply_to") or f"rudra/pc/{DEVICE_ID}/event"
            await client.publish(reply_to, json.dumps(event))
            print(f"[pc-agent] {cmd.get('action')} → ok={event['ok']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[pc-agent] shutting down")
