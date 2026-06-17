"""
Claude client — talks to Anthropic's API.

Implements the full tool-use loop: send the user's words + tool catalogue to
Claude, run whatever tools Claude chooses (via an executor callback), feed the
results back, and repeat until Claude produces a final spoken reply.

The Anthropic SDK is imported lazily so the rest of RUDRA boots even when the
package or API key is absent.
"""
from __future__ import annotations

from core.brain.llm_base import MAX_TOOL_ROUNDS, SYSTEM_PROMPT, Executor, LLMResponse, stringify
from core.config import Config
from core.log import get_logger

log = get_logger("rudra.brain.llm_anthropic")


class AnthropicLLM:
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
        """Run one conversational turn, executing tools as Claude requests them."""
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
                        "content": stringify(result),
                    })
                messages.append({"role": "user", "content": results})
                continue

            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return LLMResponse(text=text or "(no reply)", tool_calls=used)

        return LLMResponse(text="I got stuck working that out — try rephrasing.",
                            tool_calls=used)
