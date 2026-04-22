"""DevLens error hierarchy.

Every error carries a machine-readable code, a human message,
and an optional actionable fix command the user can run.
"""

from __future__ import annotations


class DevLensError(Exception):
    """Base application error."""

    code: str = "runtime_error"
    fix_command: str | None = None

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        fix_command: str | None = None,
    ) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        if fix_command is not None:
            self.fix_command = fix_command


class InvalidArgumentsError(DevLensError):
    """Raised when CLI arguments are invalid."""

    code = "invalid_arguments"


class StaticAnalysisError(DevLensError):
    """Raised when static analysis fails for a file."""

    code = "analysis_failed"


class ConfigurationError(DevLensError):
    """Raised on invalid configuration or missing env."""

    code = "config_error"


class PathSecurityError(DevLensError):
    """Raised when a path escapes the allowed project root."""

    code = "invalid_path"


class LLMUnavailableError(DevLensError):
    """Raised when Ollama model is unreachable or returns empty."""

    code = "llm_unavailable"
    fix_command = "ollama serve && ollama pull gemma2:2b"


class RetrievalError(DevLensError):
    """Raised when knowledge retrieval fails."""

    code = "retrieval_failed"


class TaskNotFoundError(DevLensError):
    """Raised when a scheduled task id does not exist."""

    code = "task_not_found"


class WatchError(DevLensError):
    """Raised when watch mode fails."""

    code = "watch_failed"


class MigrationRequiredError(DevLensError):
    """Raised when the database schema is outdated."""

    code = "schema_outdated"
    fix_command = "uv run alembic upgrade head"
