"""Application configuration loaded from environment variables only."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "HouseMind AI"
    app_version: str = "1.0.0"
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    root: Path = ROOT
    artifact_dir: Path = ROOT / "ml" / "artifacts"
    knowledge_dir: Path = ROOT / "knowledge_base"
    data_dir: Path = ROOT / "backend" / "data"
    upload_dir: Path = ROOT / "backend" / "data" / "uploads"
    chroma_dir: Path = ROOT / "backend" / "data" / "chroma"
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./backend/data/housemind.db")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
            ).split(",")
            if origin.strip()
        ]
    )
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "").strip())
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    )
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    vision_api_key: str = field(default_factory=lambda: os.getenv("VISION_API_KEY", "").strip())
    vision_base_url: str = field(
        default_factory=lambda: os.getenv(
            "VISION_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ).rstrip("/")
    )
    vision_model: str = field(default_factory=lambda: os.getenv("VISION_MODEL", "qwen3-vl-plus"))
    rag_top_k: int = field(default_factory=lambda: int(os.getenv("RAG_TOP_K", "6")))
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "8")))
    agent_rate_limit: int = field(default_factory=lambda: int(os.getenv("AGENT_RATE_LIMIT_PER_MINUTE", "30")))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def vision_remote_enabled(self) -> bool:
        return bool(self.vision_api_key)

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.upload_dir, self.chroma_dir):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
