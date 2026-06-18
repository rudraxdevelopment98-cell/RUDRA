"""
Central configuration for RUDRA.

Everything tunable lives here and is read from environment variables (.env),
so no secrets or machine-specific values are hard-coded. See .env.example.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class Config:
    # --- Identity ---
    wake_word: str = field(default_factory=lambda: _env("RUDRA_WAKE_WORD", "rudra"))
    name: str = field(default_factory=lambda: _env("RUDRA_NAME", "Rudra"))

    # --- Brain (LLM) ---
    llm_provider: str = field(default_factory=lambda: _env("RUDRA_LLM_PROVIDER", "gemini"))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: _env("RUDRA_MODEL", "claude-opus-4-8"))
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env("RUDRA_GEMINI_MODEL", "gemini-2.5-flash"))

    # --- MQTT bus ---
    mqtt_host: str = field(default_factory=lambda: _env("MQTT_HOST", "localhost"))
    mqtt_port: int = field(default_factory=lambda: int(_env("MQTT_PORT", "1883")))
    mqtt_username: str = field(default_factory=lambda: _env("MQTT_USERNAME"))
    mqtt_password: str = field(default_factory=lambda: _env("MQTT_PASSWORD"))
    mqtt_tls: bool = field(default_factory=lambda: _env("MQTT_TLS", "false").lower() == "true")

    # --- Voice (hybrid: local wake/STT, cloud TTS) ---
    voice_enabled: bool = field(default_factory=lambda: _env("RUDRA_VOICE_ENABLED", "false").lower() == "true")
    wake_model_path: str = field(default_factory=lambda: _env("RUDRA_WAKE_MODEL_PATH"))
    wake_threshold: float = field(default_factory=lambda: float(_env("RUDRA_WAKE_THRESHOLD", "0.5")))
    stt_engine: str = field(default_factory=lambda: _env("RUDRA_STT", "faster-whisper"))
    stt_model_size: str = field(default_factory=lambda: _env("RUDRA_STT_MODEL", "base.en"))
    tts_engine: str = field(default_factory=lambda: _env("RUDRA_TTS", "elevenlabs"))
    tts_api_key: str = field(default_factory=lambda: _env("TTS_API_KEY"))
    tts_voice_id: str = field(default_factory=lambda: _env("RUDRA_TTS_VOICE_ID", "Adam"))
    sample_rate: int = field(default_factory=lambda: int(_env("RUDRA_SAMPLE_RATE", "16000")))

    # --- Memory ---
    db_path: str = field(default_factory=lambda: _env("RUDRA_DB", "rudra.db"))

    # --- Server ---
    host: str = field(default_factory=lambda: _env("RUDRA_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("RUDRA_PORT", "8080")))
    # Gate the dashboard + API behind a password. Leave empty for localhost-only
    # dev; MUST be set before exposing RUDRA over a tunnel or network.
    auth_token: str = field(default_factory=lambda: _env("RUDRA_AUTH_TOKEN"))

    def validate(self) -> list[str]:
        """Return a list of human-readable warnings about missing config."""
        warnings: list[str] = []
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            warnings.append("GEMINI_API_KEY is not set — the brain cannot think yet.")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY is not set — the brain cannot think yet.")
        if self.voice_enabled and self.tts_engine == "elevenlabs" and not self.tts_api_key:
            warnings.append("TTS_API_KEY is not set — cloud voice replies are disabled.")
        if not self.auth_token and self.host not in ("127.0.0.1", "localhost"):
            warnings.append(
                "RUDRA_AUTH_TOKEN is not set but the server is bound to a non-local "
                f"address ({self.host}) — the dashboard and API are UNAUTHENTICATED. "
                "Set RUDRA_AUTH_TOKEN before exposing RUDRA beyond this machine."
            )
        if self.voice_enabled and not self.wake_model_path:
            warnings.append(
                "RUDRA_WAKE_MODEL_PATH is not set — falling back to a stock openWakeWord "
                "model instead of a model trained on the word 'rudra'."
            )
        return warnings


# A single shared instance.
config = Config()
