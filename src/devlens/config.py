from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DEFAULT_ALLOWED_EXTENSIONS: Final[tuple[str, ...]] = (".py",)
ENV_FILE_NAME: Final[str] = ".env"


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    db_url: str = "sqlite:///devlens.db"
    ollama_model: str = "qwen2.5-coder:7b"
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
    load_dotenv(ENV_FILE_NAME, override=False)
    try:
        return Settings(
            db_url=getenv("DEVLENS_DB_URL", "sqlite:///devlens.db"),
            ollama_model=getenv("DEVLENS_OLLAMA_MODEL", "qwen2.5-coder:7b"),
            ollama_embedding_model=getenv("DEVLENS_OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            vector_backend=getenv("DEVLENS_VECTOR_BACKEND", "qdrant"),
            qdrant_path=Path(getenv("DEVLENS_QDRANT_PATH", "qdrant_storage")),
            qdrant_collection=getenv("DEVLENS_QDRANT_COLLECTION", "devlens_knowledge"),
            project_root=Path(getenv("DEVLENS_PROJECT_ROOT", ".")),
            max_file_size_kb=int(getenv("DEVLENS_MAX_FILE_SIZE_KB", "512")),
            allowed_extensions_raw=getenv("DEVLENS_ALLOWED_EXTENSIONS", ".py"),
            llm_timeout_seconds=int(getenv("DEVLENS_LLM_TIMEOUT_SECONDS", "30")),
            cache_enabled=getenv("DEVLENS_CACHE_ENABLED", "true").lower()
            in {"1", "true", "yes", "on"},
            log_level=getenv("DEVLENS_LOG_LEVEL", "INFO"),
        )
    except ValidationError as exc:
        raise RuntimeError(f"Invalid DevLens configuration: {exc}") from exc


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig(settings=get_settings())
