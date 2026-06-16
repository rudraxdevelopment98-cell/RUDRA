"""
Claude client — the one place RUDRA talks to the LLM.

Keeping this isolated means the model, system prompt, and tool wiring live in a
single file. Everything else just calls `LLM.think(...)`.

Phase 0: stubbed. Phase 1: wire the real Anthropic SDK (see TODOs).
"""
from __future__ import annotations

from dataclasses import dataclass

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.brain.llm")

SYSTEM_PROMPT = """You are RUDRA, a personal voice-driven AI command center —
like JARVIS. You control the user's PC, phone, smart-home devices, and custom
electronics by calling tools. Be concise and natural; you are spoken aloud.
When a request maps to one or more tools, call them. For anything dangerous
(power off, delete, unlock) ask for confirmation first. If you cannot do
something, say so plainly."""


@dataclass
class LLMResponse:
    """What the brain gets back from one turn."""
    text: str                       # spoken reply
    tool_calls: list[dict]          # [{"name": "pc.open_app", "args": {...}}]


class LLM:
    def __init__(self, config: Config):
        self.config = config
        self._client = None  # lazily created Anthropic client

    def _ensure_client(self):
        # TODO(Phase 1): create the Anthropic client.
        #   from anthropic import AsyncAnthropic
        #   self._client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        if not self.config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot reach the brain.")
        return self._client

    async def think(self, user_text: str, tools: list[dict], history: list[dict]) -> LLMResponse:
        """
        Send the user's words (plus the tool catalogue and recent history) to
        Claude and return its reply + any tool calls it chose.

        Args:
            user_text: what the user said, transcribed.
            tools:     the tool catalogue from intents.build_tool_catalogue().
            history:   recent conversation turns for context.
        """
        # TODO(Phase 1): real call —
        #   resp = await self._client.messages.create(
        #       model=self.config.model,
        #       system=SYSTEM_PROMPT,
        #       tools=tools,
        #       messages=[*history, {"role": "user", "content": user_text}],
        #       max_tokens=1024,
        #   )
        #   parse resp.content for text blocks and tool_use blocks.
        log.info("🧠 (stub) think: %r  | %d tools available", user_text, len(tools))
        return LLMResponse(
            text=f"(skeleton) I heard: {user_text!r}. The brain is not wired yet.",
            tool_calls=[],
        )
