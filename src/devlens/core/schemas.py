from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class StaticAnalysisMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    function_count: int = 0
    class_count: int = 0
    import_count: int = 0
    loop_count: int = 0
    conditional_count: int = 0
    return_count: int = 0
    max_nesting_depth: int = 0
    recursion_detected: bool = False
    cyclomatic_complexity: float = 0.0
    long_function_count: int = 0


class FileAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_path: Path
    relative_path: Path
    content_hash: str
    language: str = "python"
    metrics: StaticAnalysisMetrics
    issues: list[str] = Field(default_factory=list)
    llm_result: LLMAnalysisResult | None = None
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    feedback: GeneratedFeedback | None = None


class AnalyzeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files_scanned: int
    files_analyzed: int
    submissions_saved: int
    analyses_saved: int
    skipped_files: int
    deduplicated_files: int
    total_complexity: float
    max_nesting_depth: int
    recursion_file_count: int


class LLMAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patterns: list[str] = Field(default_factory=list)
    optimization_assessment: str = ""
    critique: str = ""
    confidence: float = 0.0
    fallback_used: bool = False
    error: str | None = None


class SkillAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_name: str
    category: str
    score: float
    confidence: float
    reason: str


class GeneratedFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critique: str
    questions: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)


class ScheduledTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    related_file_path: str | None = None
    priority: str = "medium"
    due_in_days: int = 3


class ChatReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    fallback_used: bool = False
    matched_chunks: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    error_reason: str | None = None
    error_code: str | None = None
