"""
The tool catalogue — what Claude is allowed to do.

Each Skill declares its tools (name + description + JSON schema for args). This
module gathers them into the format the Anthropic tool-use API expects. Claude
picks a tool; the orchestrator routes it to the owning Skill.

Adding a capability = adding a tool spec in a Skill, not editing this file.
"""
from __future__ import annotations

from core.log import get_logger

log = get_logger("rudra.brain.intents")


def build_tool_catalogue(skills: dict) -> list[dict]:
    """
    Flatten every skill's `tools` into one list for the LLM.

    Returns a list of Anthropic tool specs:
        {"name": "pc.open_app",
         "description": "...",
         "input_schema": {"type": "object", "properties": {...}}}
    """
    catalogue: list[dict] = []
    for skill in skills.values():
        for tool in skill.tools():
            catalogue.append(tool)
    log.debug("Built tool catalogue with %d tools", len(catalogue))
    return catalogue
