"""
MQTT topic contract — the single source of truth for topic names.

Format:  rudra/<domain>/<device>/<channel>     (see docs/PROTOCOL.md)
"""
from __future__ import annotations

ROOT = "rudra"

# Channels (the last segment of a topic).
CMD = "cmd"            # brain → agent
EVENT = "event"        # agent → brain
STATE = "state"        # agent → bus (retained)
REGISTER = "register"  # agent → brain on connect

# Domains.
PC = "pc"
PHONE = "phone"
IOT = "iot"
NODE = "node"          # custom electronics (ESP32)
SYSTEM = "system"


def topic(domain: str, device: str, channel: str) -> str:
    """Build a topic: topic('pc', 'main-pc', CMD) -> 'rudra/pc/main-pc/cmd'."""
    return f"{ROOT}/{domain}/{device}/{channel}"


def sub_all(channel: str) -> str:
    """Wildcard subscription across all domains/devices for one channel."""
    return f"{ROOT}/+/+/{channel}"


# Topic every agent uses to announce itself.
REGISTER_ALL = f"{ROOT}/{SYSTEM}/all/{REGISTER}"
