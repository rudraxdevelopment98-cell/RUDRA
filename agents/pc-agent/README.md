# RUDRA — PC Agent

Runs on the computer you want RUDRA to control.

## What it does
Connects to the MQTT bus, tells the brain what it can do, then listens for
commands (`open app`, `run script`, `volume`, `power`, `search files`) and
reports results back.

## Safety
- Only apps/scripts in `ALLOW_LIST` (in `agent.py`) can run.
- Power actions (lock/sleep/shutdown) require a **confirmed** command.

## Setup (Phase 3)
```bash
pip install -r requirements.txt
export MQTT_HOST=<brain-host>     # where the broker runs
export RUDRA_PC_ID=main-pc        # this PC's id
python agent.py
```

Status: 🟡 skeleton — handlers land in Phase 3.
