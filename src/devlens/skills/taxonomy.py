from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    category: str


SKILL_TAXONOMY: tuple[SkillDefinition, ...] = (
    SkillDefinition(name="Recursion", category="DSA"),
    SkillDefinition(name="Optimization Thinking", category="Engineering"),
    SkillDefinition(name="Modularity", category="Engineering"),
    SkillDefinition(name="Edge Case Handling", category="Engineering"),
    SkillDefinition(name="Code Readability", category="Engineering"),
)
