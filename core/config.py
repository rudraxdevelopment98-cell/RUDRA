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

    # --- Brain (Claude LLM) ---
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: _env("RUDRA_MODEL", "claude-opus-4-8"))

    # --- MQTT bus ---
    mqtt_host: str = field(default_factory=lambda: _env("MQTT_HOST", "localhost"))
    mqtt_port: int = field(default_factory=lambda: int(_env("MQTT_PORT", "1883")))
    mqtt_username: str = field(default_factory=lambda: _env("MQTT_USERNAME"))
    mqtt_password: str = field(default_factory=lambda: _env("MQTT_PASSWORD"))

    # --- Voice (hybrid: local wake/STT, cloud TTS) ---
    stt_engine: str = field(default_factory=lambda: _env("RUDRA_STT", "faster-whisper"))
    tts_engine: str = field(default_factory=lambda: _env("RUDRA_TTS", "cloud"))
    tts_api_key: str = field(default_factory=lambda: _env("TTS_API_KEY"))

    # --- Memory ---
    db_path: str = field(default_factory=lambda: _env("RUDRA_DB", "rudra.db"))

    # --- Server ---
    host: str = field(default_factory=lambda: _env("RUDRA_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(_env("RUDRA_PORT", "8080")))

    def validate(self) -> list[str]:
        """Return a list of human-readable warnings about missing config."""
        warnings: list[str] = []
        if not self.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY is not set — the brain cannot think yet.")
        if self.tts_engine == "cloud" and not self.tts_api_key:
            warnings.append("TTS_API_KEY is not set — cloud voice replies are disabled.")
        return warnings


# A single shared instance.
config = Config()
