"""CleanSlate Application Configuration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _load_env() -> None:
    possible_paths = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(".env"),
    ]
    for p in possible_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env()


class Settings:
    def __init__(self) -> None:
        self.PROJECT_NAME: str = os.getenv("PROJECT_NAME", "CleanSlate")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
        self.ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

        # Security
        self.DATA_ENCRYPTION_KEY: str = os.getenv(
            "DATA_ENCRYPTION_KEY", "dGhpcy1pcy1hLTMyLWJ5dGUtZGV2LWtleS0xMjM0NTY3ODk="
        )
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY", "cleanslate-dev-jwt-secret-key-32-chars-long-minimum!"
        )
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # Database & Cache
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cleanslate.db")
        self.REDIS_URL: str = os.getenv("REDIS_URL", "")

        # LLM Settings
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none")
        default_base_url = "https://api.groq.com/openai/v1" if self.LLM_PROVIDER == "groq" else ""
        self.LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", default_base_url) or default_base_url
        self.LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
        default_model = "openai/gpt-oss-120b" if self.LLM_PROVIDER == "groq" else "heuristic"
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", default_model)
        self.LLM_TIMEOUT_S: int = int(os.getenv("LLM_TIMEOUT_S", "30"))

        # Storage & Upload Guardrails
        self.STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
        self.MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", "209715200"))
        self.MAX_COLUMNS: int = int(os.getenv("MAX_COLUMNS", "2000"))
        self.MAX_FIELD_LENGTH: int = int(os.getenv("MAX_FIELD_LENGTH", "100000"))
        self.MAX_HEADER_LENGTH: int = int(os.getenv("MAX_HEADER_LENGTH", "1000"))
        self.MAX_PARSE_TIME_SECONDS: int = int(os.getenv("MAX_PARSE_TIME_SECONDS", "60"))
        self.ZIP_MAX_EXPANSION_RATIO: int = int(os.getenv("ZIP_MAX_EXPANSION_RATIO", "100"))
        self.ZIP_MAX_UNCOMPRESSED_BYTES: int = int(os.getenv("ZIP_MAX_UNCOMPRESSED_BYTES", "524288000"))
        self.IN_MEMORY_MAX_ROWS: int = int(os.getenv("IN_MEMORY_MAX_ROWS", "2000000"))
        self.MIN_ROWS_FOR_INFERENCE: int = int(os.getenv("MIN_ROWS_FOR_INFERENCE", "30"))
        self.SPARSE_THRESHOLD: float = float(os.getenv("SPARSE_THRESHOLD", "0.90"))
        self.IMPUTE_MAX_NULL_RATE: float = float(os.getenv("IMPUTE_MAX_NULL_RATE", "0.30"))

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
