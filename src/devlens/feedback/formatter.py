from __future__ import annotations

from devlens.core.schemas import GeneratedFeedback


def format_feedback(feedback: GeneratedFeedback) -> str:
    lines = [feedback.critique]
    if feedback.questions:
        lines.append("Questions:")
        lines.extend(f"- {question}" for question in feedback.questions)
    if feedback.tasks:
        lines.append("Tasks:")
        lines.extend(f"- {task}" for task in feedback.tasks)
    return "\n".join(lines)
