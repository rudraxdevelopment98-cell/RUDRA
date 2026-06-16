"""
Claude client — the one place RUDRA talks to the LLM.

Implements the full tool-use loop: send the user's words + tool catalogue to
Claude, run whatever tools Claude chooses (via an executor callback), feed the
results back, and repeat until Claude produces a final spoken reply.

The Anthropic SDK is imported lazily so the rest of RUDRA boots even when the
package or API key is absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from core.config import Config
from core.log import get_logger

log = get_logger("rudra.brain.llm")

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


class LLM:
    def __init__(self, config: Config):
        self.config = config
        self._client = None  # lazily created Anthropic client

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot reach the brain.")
        from anthropic import AsyncAnthropic  # lazy import

        self._client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        return self._client

    async def think(
        self,
        user_text: str,
        tools: list[dict],
        history: list[dict],
        executor: Executor,
    ) -> LLMResponse:
        """
        Run one conversational turn, executing tools as Claude requests them.

        Args:
            user_text: what the user said.
            tools:     the tool catalogue from intents.build_tool_catalogue().
            history:   prior turns as [{"role","content"}].
            executor:  async fn(tool_name, args) -> result dict.
        """
        client = self._ensure_client()
        messages: list[dict] = [*history, {"role": "user", "content": user_text}]
        used: list[dict] = []

        for _ in range(MAX_TOOL_ROUNDS):
            resp = await client.messages.create(
                model=self.config.model,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
                max_tokens=1024,
            )

            # Collect any tool_use blocks; run them and feed results back.
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason == "tool_use" and tool_uses:
                messages.append({"role": "assistant", "content": resp.content})
                results = []
                for block in tool_uses:
                    used.append({"name": block.name, "args": block.input})
                    log.info("🔧 tool: %s(%s)", block.name, block.input)
                    result = await executor(block.name, dict(block.input))
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": _stringify(result),
                    })
                messages.append({"role": "user", "content": results})
                continue

            # No more tools → final answer.
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return LLMResponse(text=text or "(no reply)", tool_calls=used)

        return LLMResponse(text="I got stuck working that out — try rephrasing.",
                           tool_calls=used)


def _stringify(result: dict) -> str:
    import json

    return json.dumps(result)
