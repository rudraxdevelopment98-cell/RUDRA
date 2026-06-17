"""
LLM factory — the one place RUDRA picks which provider's brain to use.

RUDRA can talk to more than one LLM provider (Claude, Gemini, …) behind one
interface: `LLM(config).think(text, tools, history, executor)`. Which
provider actually runs is controlled by `config.llm_provider`, so the rest of
the system (orchestrator, skills, tests) never needs to know or care.
"""
from __future__ import annotations

from core.brain.llm_base import Executor, LLMResponse  # re-exported for callers
from core.config import Config
from core.log import get_logger

log = get_logger("rudra.brain.llm")


class LLM:
    def __init__(self, config: Config):
        self.config = config
        self._impl = self._build_impl(config)

    @staticmethod
    def _build_impl(config: Config):
        provider = config.llm_provider.lower()
        if provider == "gemini":
            from core.brain.llm_gemini import GeminiLLM

            return GeminiLLM(config)
        if provider == "anthropic":
            from core.brain.llm_anthropic import AnthropicLLM

            return AnthropicLLM(config)
        raise RuntimeError(f"Unknown RUDRA_LLM_PROVIDER: {provider!r}")

    async def think(
        self,
        user_text: str,
        tools: list[dict],
        history: list[dict],
        executor: Executor,
    ) -> LLMResponse:
        return await self._impl.think(user_text, tools, history, executor)
