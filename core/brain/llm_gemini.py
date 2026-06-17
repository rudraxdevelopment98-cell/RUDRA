"""
Gemini client — talks to Google's Generative AI API.

Same tool-use loop contract as `llm_anthropic.AnthropicLLM`, but speaks
Gemini's function-calling shape: tool specs become `function_declarations`
with upper-case JSON-schema types, conversation roles are `user`/`model`, and
tool results go back as `function_response` parts.

The `google-generativeai` SDK is imported lazily so the rest of RUDRA boots
even when the package or API key is absent.
"""
from __future__ import annotations

from core.brain.llm_base import MAX_TOOL_ROUNDS, SYSTEM_PROMPT, Executor, LLMResponse
from core.config import Config
from core.log import get_logger

log = get_logger("rudra.brain.llm_gemini")

_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
}


def _convert_schema(schema: dict) -> dict:
    """Translate a JSON-schema fragment (lower-case types) into Gemini's shape."""
    out: dict = {}
    json_type = schema.get("type", "object")
    out["type"] = _TYPE_MAP.get(json_type, json_type.upper())
    if "description" in schema:
        out["description"] = schema["description"]
    if "enum" in schema:
        out["enum"] = schema["enum"]
    if json_type == "object" and "properties" in schema:
        out["properties"] = {k: _convert_schema(v) for k, v in schema["properties"].items()}
        if schema.get("required"):
            out["required"] = schema["required"]
    if json_type == "array" and "items" in schema:
        out["items"] = _convert_schema(schema["items"])
    return out


def _convert_tools(tools: list[dict]) -> list[dict]:
    """Translate RUDRA's Anthropic-style tool specs into Gemini function_declarations."""
    declarations = []
    for t in tools:
        declarations.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": _convert_schema(t["input_schema"]),
        })
    return [{"function_declarations": declarations}]


class GeminiLLM:
    def __init__(self, config: Config):
        self.config = config
        self._model = None  # lazily created GenerativeModel

    def _ensure_model(self, tools: list[dict]):
        if not self.config.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set — cannot reach the brain.")
        import google.generativeai as genai  # lazy import

        genai.configure(api_key=self.config.gemini_api_key)
        return genai.GenerativeModel(
            model_name=self.config.gemini_model,
            system_instruction=SYSTEM_PROMPT,
            tools=_convert_tools(tools) if tools else None,
        )

    async def think(
        self,
        user_text: str,
        tools: list[dict],
        history: list[dict],
        executor: Executor,
    ) -> LLMResponse:
        """Run one conversational turn, executing tools as Gemini requests them."""
        model = self._ensure_model(tools)
        contents = _history_to_gemini(history)
        contents.append({"role": "user", "parts": [{"text": user_text}]})
        used: list[dict] = []

        for _ in range(MAX_TOOL_ROUNDS):
            resp = await model.generate_content_async(contents)
            candidate = resp.candidates[0]
            parts = candidate.content.parts
            function_calls = [p.function_call for p in parts if p.function_call]

            if function_calls:
                contents.append({"role": "model", "parts": list(parts)})
                response_parts = []
                for fc in function_calls:
                    args = dict(fc.args) if fc.args else {}
                    used.append({"name": fc.name, "args": args})
                    log.info("🔧 tool: %s(%s)", fc.name, args)
                    result = await executor(fc.name, args)
                    response_parts.append({
                        "function_response": {"name": fc.name, "response": result}
                    })
                contents.append({"role": "function", "parts": response_parts})
                continue

            text = "".join(p.text for p in parts if getattr(p, "text", "")).strip()
            return LLMResponse(text=text or "(no reply)", tool_calls=used)

        return LLMResponse(text="I got stuck working that out — try rephrasing.",
                            tool_calls=used)


def _history_to_gemini(history: list[dict]) -> list[dict]:
    """Map RUDRA's stored {role: user/assistant, content: str} turns to Gemini's shape."""
    contents = []
    for turn in history:
        role = "model" if turn.get("role") == "assistant" else "user"
        content = turn.get("content", "")
        if isinstance(content, str):
            contents.append({"role": role, "parts": [{"text": content}]})
    return contents
