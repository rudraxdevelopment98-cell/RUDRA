"""
Skill registry.

`load_skills` builds every skill and returns them keyed by domain. To add a new
capability area, create a Skill subclass and add it to SKILL_CLASSES.
"""
from __future__ import annotations

from core.bus.mqtt import Bus
from core.memory.store import Memory
from core.skills.base import Skill
from core.skills.electronics import ElectronicsSkill
from core.skills.iot import IoTSkill
from core.skills.pc import PCSkill
from core.skills.phone import PhoneSkill
from core.skills.recall import RecallSkill
from core.skills.system import SystemSkill

SKILL_CLASSES: list[type[Skill]] = [
    SystemSkill,
    PCSkill,
    PhoneSkill,
    IoTSkill,
    ElectronicsSkill,
    RecallSkill,
]


def load_skills(bus: Bus, memory: Memory) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for cls in SKILL_CLASSES:
        skill = cls(bus, memory)
        skills[skill.domain] = skill
    # The system skill introspects every other skill for "what can you do".
    if "system" in skills:
        skills["system"].all_skills = skills
    return skills
