from __future__ import annotations


def compute_updated_skill_score(
    previous_score: float,
    current_score: float,
    learning_rate: float = 0.4,
) -> float:
    return previous_score + (current_score - previous_score) * learning_rate
