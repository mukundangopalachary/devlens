from __future__ import annotations

import json
from typing import Any, cast

import ollama
from sqlalchemy.orm import Session

from devlens.analysis.llm.parser import parse_llm_response
from devlens.analysis.llm.prompts import build_analysis_prompt
from devlens.cache.prompt_cache import build_prompt_hash
from devlens.cache.result_cache import get_cached_response, store_cached_response
from devlens.config import get_settings
from devlens.core.schemas import LLMAnalysisResult, StaticAnalysisMetrics


def analyze_with_llm(
    session: Session,
    source: str,
    metrics: StaticAnalysisMetrics,
    issues: list[str],
) -> LLMAnalysisResult:
    settings = get_settings()
    prompt = build_analysis_prompt(source=source, metrics=metrics, issues=issues)
    prompt_hash = build_prompt_hash("analysis", settings.ollama_model, prompt)
    if settings.cache_enabled:
        cached_response = get_cached_response(session, prompt_hash, cache_kind="analysis")
        if cached_response is not None:
            parsed = parse_llm_response(cached_response)
            parsed.fallback_used = False
            return parsed
    try:
        response = cast(
            dict[str, Any],
            ollama.generate(
                model=settings.ollama_model,
                prompt=prompt,
                options={"temperature": 0.1},
            ),
        )
        raw_text = str(response.get("response", ""))
        parsed = parse_llm_response(raw_text)
        if not parsed.critique:
            raise ValueError("LLM response missing critique.")
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="analysis",
                model_name=settings.ollama_model,
                prompt_text=prompt,
                response_text=json.dumps(parsed.model_dump(), sort_keys=True),
            )
        return parsed
    except Exception as exc:
        return LLMAnalysisResult(
            patterns=_fallback_patterns(metrics),
            optimization_assessment=_fallback_optimization_assessment(metrics),
            critique=_fallback_critique(metrics, issues),
            confidence=0.25,
            fallback_used=True,
            error=str(exc),
        )


def embed_text(session: Session, text: str) -> list[float]:
    settings = get_settings()
    prompt_hash = build_prompt_hash("embed", settings.ollama_embedding_model, text)
    if settings.cache_enabled:
        cached_response = get_cached_response(session, prompt_hash, cache_kind="embedding")
        if cached_response is not None:
            return [float(item) for item in json.loads(cached_response)]

    try:
        response = cast(
            dict[str, Any],
            ollama.embed(model=settings.ollama_embedding_model, input=text),
        )
        embeddings = cast(list[list[float]], response.get("embeddings", []))
        if not embeddings:
            raise ValueError("No embeddings returned.")
        vector = embeddings[0]
        if settings.cache_enabled:
            store_cached_response(
                session=session,
                prompt_hash=prompt_hash,
                cache_kind="embedding",
                model_name=settings.ollama_embedding_model,
                prompt_text=text,
                response_text=json.dumps(vector),
            )
        return vector
    except Exception:
        return []


def _fallback_patterns(metrics: StaticAnalysisMetrics) -> list[str]:
    patterns: list[str] = []
    if metrics.recursion_detected:
        patterns.append("recursion")
    if metrics.loop_count > 0:
        patterns.append("iterative traversal")
    if metrics.conditional_count > 0:
        patterns.append("branching logic")
    return patterns


def _fallback_optimization_assessment(metrics: StaticAnalysisMetrics) -> str:
    if metrics.cyclomatic_complexity >= 10 or metrics.max_nesting_depth >= 4:
        return "Optimization opportunity exists due to control-flow complexity."
    return "Structure is acceptable for current scope, but detailed model review is unavailable."


def _fallback_critique(metrics: StaticAnalysisMetrics, issues: list[str]) -> str:
    if issues:
        return f"Fallback critique: {' '.join(issues)}"
    if metrics.loop_count == 0 and metrics.function_count <= 1:
        return "Fallback critique: simple structure, limited signal."
    return "Fallback critique: static signals collected, LLM review unavailable."
