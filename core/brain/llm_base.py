"""
Shared types for LLM backends.

RUDRA can talk to more than one LLM provider (Claude, Gemini, …) behind one
interface — see `core/brain/llm.py` for the factory that picks one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

SYSTEM_PROMPT = """You are RUDRA, a personal voice-driven AI command center —
like JARVIS. You control the user's PC, phone, smart-home devices, and custom
electronics by calling tools. Be concise and natural; your replies are spoken
aloud, so avoid lists and markdown. When a request maps to one or more tools,
call them. For anything dangerous (power off, delete, unlock) confirm first.
If a tool reports a device isn't online yet, say so plainly rather than
pretending it worked."""

# An executor runs one tool call and returns a JSON-able result dict.
Executor = Callable[[str, dict], Awaitable[dict]]

# Safety valve so a confused model can't loop forever.
MAX_TOOL_ROUNDS = 6


@dataclass
class LLMResponse:
    """The outcome of one full turn (after any tool calls)."""
    text: str                                   # spoken reply
    tool_calls: list[dict] = field(default_factory=list)  # [{"name","args"}] for logging


def stringify(result: dict) -> str:
    import json

    return json.dumps(result)
