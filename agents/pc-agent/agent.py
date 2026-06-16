"""
RUDRA PC Agent.

Runs on the computer you want to control. It:
  1. connects to the MQTT bus,
  2. announces itself (register) with its capabilities,
  3. listens on  rudra/pc/<this-pc>/cmd  and executes allow-listed actions,
  4. reports the result on  rudra/pc/<this-pc>/event.

Security: only apps/scripts in ALLOW_LIST may run; power actions require a
confirmed command (see docs/PROTOCOL.md).

Phase 0: skeleton. Phase 3: implement the handlers.

Run:
    pip install -r requirements.txt
    python agent.py
"""
from __future__ import annotations

import os
import platform

DEVICE_ID = os.environ.get("RUDRA_PC_ID", "main-pc")

CAPABILITIES = ["pc.open_app", "pc.run_script", "pc.volume", "pc.power", "pc.search_files"]

# Only these may be launched/run. Edit to taste.
ALLOW_LIST = {
    "apps": ["code", "chrome", "firefox", "spotify", "terminal"],
    "scripts": [],  # e.g. "backup", "build"
}


def register_payload() -> dict:
    return {
        "device": DEVICE_ID,
        "domain": "pc",
        "capabilities": CAPABILITIES,
        "meta": {"os": platform.system().lower(), "agent": "0.1.0"},
    }


def handle_command(cmd: dict) -> dict:
    """Execute one command, return an Event dict. (TODO Phase 3)"""
    action = cmd.get("action")
    # TODO(Phase 3): implement per action, honouring ALLOW_LIST and needs_confirm:
    #   pc.open_app     → subprocess / os.startfile, only if app in ALLOW_LIST["apps"]
    #   pc.run_script   → run named script from ALLOW_LIST["scripts"]
    #   pc.volume       → platform volume control
    #   pc.power        → require cmd["confirmed"] before lock/sleep/shutdown
    #   pc.search_files → walk/index and return matches
    return {"in_reply_to": cmd.get("id"), "ok": False,
            "error": f"not implemented yet: {action}", "result": None}


def main() -> None:
    print(f"[pc-agent] {DEVICE_ID} on {platform.system()} — skeleton")
    print(f"[pc-agent] capabilities: {', '.join(CAPABILITIES)}")
    # TODO(Phase 3):
    #   - connect to MQTT (host/port from env)
    #   - publish register_payload() to rudra/system/all/register
    #   - subscribe rudra/pc/<DEVICE_ID>/cmd → handle_command → publish event
    print("[pc-agent] (not connected — implement in Phase 3)")


if __name__ == "__main__":
    main()
