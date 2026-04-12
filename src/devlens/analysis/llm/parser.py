from __future__ import annotations

import json
from typing import Any, cast

from devlens.core.schemas import LLMAnalysisResult


def parse_llm_response(raw_text: str) -> LLMAnalysisResult:
    payload = _extract_json(raw_text)
    patterns_raw = payload.get("patterns", [])
    confidence_raw = payload.get("confidence", 0.0)
    return LLMAnalysisResult(
        patterns=[str(item) for item in cast(list[object], patterns_raw)],
        optimization_assessment=str(payload.get("optimization_assessment", "")),
        critique=str(payload.get("critique", "")),
        confidence=float(cast(float | int | str, confidence_raw)),
    )


def _extract_json(raw_text: str) -> dict[str, object]:
    stripped = raw_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return cast(dict[str, Any], json.loads(stripped))

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return cast(dict[str, Any], json.loads(stripped[start : end + 1]))
