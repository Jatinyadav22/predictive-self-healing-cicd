import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Ollama Local Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_REASONING_MODEL: str = "qwen2.5:3b"
    LLM_CODE_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"

    # Storage Paths
    DATABASE_PATH: Path = Path("data/platform.db")
    AUDIT_LOG_PATH: Path = Path("data/audit.jsonl")
    MODELS_DIR: Path = Path("src/models/saved_models")
    DEMO_REPO_PATH: Path = Path("demo_repo")

    # Guardrails
    AUTO_APPLY_MAX_RISK: float = 40.0
    MAX_PATCH_LINES: int = 50
    MAX_LLM_TIMEOUT_SECONDS: int = 180

    # Sourcegraph
    SOURCEGRAPH_URL: str = "http://localhost:7080"
    SOURCEGRAPH_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
