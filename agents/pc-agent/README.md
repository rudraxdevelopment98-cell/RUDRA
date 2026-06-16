# RUDRA — PC Agent

Runs on the computer you want RUDRA to control.

## What it does
Connects to the MQTT bus, tells the brain what it can do, then listens for
commands (`open app`, `run script`, `volume`, `power`, `search files`) and
reports results back.

## Safety
- Only apps/scripts in `ALLOW_LIST_APPS` / `ALLOW_LIST_SCRIPTS` (in `agent.py`)
  can run — edit these to taste.
- Power actions (lock/sleep/shutdown) are refused unless the command carries
  `"confirmed": true`. The brain asks you first, then sends the confirmed command.
- `pc.search_files` only looks under `RUDRA_SEARCH_ROOT` (default: your home dir).

## Cross-platform notes
- **Volume:** macOS uses `osascript`; Linux uses `pactl`/`amixer`; Windows needs
  the optional `pycaw` + `comtypes` packages.
- **Power:** uses `loginctl`/`systemctl` (Linux), `pmset`/`osascript` (macOS),
  `rundll32`/`shutdown` (Windows).

## Setup
```bash
pip install -r requirements.txt
export MQTT_HOST=<brain-host>     # where the broker runs
export RUDRA_PC_ID=main-pc        # this PC's id
python agent.py
```

Status: 🟢 implemented (Phase 3).
