from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path
from subprocess import run
from typing import Final

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DEFAULT_ALLOWED_EXTENSIONS: Final[tuple[str, ...]] = (".py",)
ENV_FILE_NAME: Final[str] = ".env"


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    db_url: str = "sqlite:///devlens.db"
    ollama_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    vector_backend: str = "qdrant"
    qdrant_path: Path = Path("qdrant_storage")
    qdrant_collection: str = "devlens_knowledge"
    project_root: Path = Path(".")
    max_file_size_kb: int = Field(default=512, ge=1)
    allowed_extensions_raw: str = ".py"
    llm_timeout_seconds: int = Field(default=30, ge=1)
    cache_enabled: bool = True
    log_level: str = "INFO"
    ollama_num_ctx: int = Field(default=2048, ge=256)
    ollama_analysis_num_predict: int = Field(default=256, ge=32)
    ollama_chat_num_predict: int = Field(default=384, ge=32)
    ollama_keep_alive: str = "5m"

    @property
    def allowed_extensions(self) -> tuple[str, ...]:
        extensions = tuple(
            normalized
            for item in self.allowed_extensions_raw.split(",")
            if (normalized := _normalize_extension(item))
        )
        return extensions or DEFAULT_ALLOWED_EXTENSIONS

    @property
    def resolved_project_root(self) -> Path:
        return self.project_root.expanduser().resolve()

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_kb * 1024


@dataclass(frozen=True)
class AppConfig:
    settings: Settings

    @property
    def database_url(self) -> str:
        return self.settings.db_url


def _normalize_extension(raw_extension: str) -> str:
    cleaned = raw_extension.strip()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith(".") else f".{cleaned}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    project_root_default = _detect_project_root()
    env_file = _find_env_file(project_root_default)
    if env_file is not None:
        load_dotenv(env_file, override=False)

    project_root = Path(getenv("DEVLENS_PROJECT_ROOT", str(project_root_default)))
    db_url_default = _default_db_url(project_root)
    qdrant_path_default = _resolve_path_from_root(project_root, Path("qdrant_storage"))
    try:
        return Settings(
            db_url=_normalize_db_url(_env_value("DEVLENS_DB_URL", db_url_default), project_root),
            ollama_model=_env_value("DEVLENS_OLLAMA_MODEL", "llama3.2:3b"),
            ollama_embedding_model=_env_value("DEVLENS_OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            vector_backend=_env_value("DEVLENS_VECTOR_BACKEND", "qdrant"),
            qdrant_path=_resolve_path_from_root(
                project_root,
                Path(_env_value("DEVLENS_QDRANT_PATH", str(qdrant_path_default))),
            ),
            qdrant_collection=_env_value("DEVLENS_QDRANT_COLLECTION", "devlens_knowledge"),
            project_root=project_root,
            max_file_size_kb=_env_int("DEVLENS_MAX_FILE_SIZE_KB", 512),
            allowed_extensions_raw=_env_value("DEVLENS_ALLOWED_EXTENSIONS", ".py"),
            llm_timeout_seconds=_env_int("DEVLENS_LLM_TIMEOUT_SECONDS", 30),
            cache_enabled=_env_bool("DEVLENS_CACHE_ENABLED", True),
            log_level=_env_value("DEVLENS_LOG_LEVEL", "INFO"),
            ollama_num_ctx=_env_int("DEVLENS_OLLAMA_NUM_CTX", 2048),
            ollama_analysis_num_predict=_env_int("DEVLENS_OLLAMA_ANALYSIS_NUM_PREDICT", 256),
            ollama_chat_num_predict=_env_int("DEVLENS_OLLAMA_CHAT_NUM_PREDICT", 384),
            ollama_keep_alive=_env_value("DEVLENS_OLLAMA_KEEP_ALIVE", "5m"),
        )
    except ValidationError as exc:
        raise RuntimeError(f"Invalid DevLens configuration: {exc}") from exc


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig(settings=get_settings())


def _detect_project_root() -> Path:
    env_root = getenv("DEVLENS_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    cwd = Path.cwd().resolve()
    git_result = run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_result.returncode == 0:
        raw = git_result.stdout.strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return cwd


def _find_env_file(project_root: Path) -> str | None:
    current = Path.cwd().resolve()
    candidates: list[Path] = []
    while True:
        candidates.append(current / ENV_FILE_NAME)
        if current == project_root or current.parent == current:
            break
        current = current.parent
    candidates.append(project_root / ENV_FILE_NAME)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def _default_db_url(project_root: Path) -> str:
    return f"sqlite:///{(project_root / 'devlens.db').resolve()}"


def _normalize_db_url(db_url: str, project_root: Path) -> str:
    if not db_url.startswith("sqlite:///"):
        return db_url
    raw_path = Path(db_url.removeprefix("sqlite:///"))
    if raw_path.is_absolute():
        return db_url
    resolved = (project_root / raw_path).resolve()
    return f"sqlite:///{resolved}"


def _resolve_path_from_root(project_root: Path, candidate: Path) -> Path:
    expanded = candidate.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (project_root / expanded).resolve()


def _env_value(name: str, default: str) -> str:
    raw = getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()
    if not cleaned:
        return default
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return default
    return cleaned


def _env_int(name: str, default: int) -> int:
    value = _env_value(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for {name}: {value}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()
    cleaned = cleaned.lower()
    if not cleaned or (cleaned.startswith("<") and cleaned.endswith(">")):
        return default
    if cleaned in {"1", "true", "yes", "on"}:
        return True
    if cleaned in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid boolean for {name}: {raw}")
