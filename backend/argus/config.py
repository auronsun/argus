"""Runtime configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- LLM providers ----
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    anthropic_model: str = "claude-opus-4-7"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-pro"
    qwen_api_key: str = ""
    qwen_model: str = "qwen-plus"
    nvidia_api_key: str = ""
    nvidia_model: str = "minimaxai/minimax-m2.7"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    ollama_host: str = ""
    ollama_model: str = "llama3.1"

    # ---- Market data ----
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    tushare_token: str = ""
    longbridge_app_key: str = ""
    longbridge_app_secret: str = ""
    longbridge_access_token: str = ""

    # ---- Server ----
    argus_host: str = "127.0.0.1"
    argus_port: int = 8765
    argus_db_path: str = "./data/argus.sqlite"
    argus_cache_dir: str = "./data/cache"
    argus_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    argus_cors_origins: str = ""

    # Max concurrent analyst LLM calls in a committee run. 3 is safe on most
    # free LLM tiers (NVIDIA NIM, DeepSeek free) which cap concurrent streams;
    # raise to 5 (or higher) if you're paying for a tier with no such cap.
    argus_committee_concurrency: int = 3

    @property
    def cors_origins(self) -> list[str]:
        defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
        extra = [o.strip() for o in self.argus_cors_origins.split(",") if o.strip()]
        return list(dict.fromkeys(defaults + extra))

    @property
    def db_path(self) -> Path:
        p = (PROJECT_ROOT / self.argus_db_path).resolve() if not Path(self.argus_db_path).is_absolute() else Path(self.argus_db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cache_dir(self) -> Path:
        p = (PROJECT_ROOT / self.argus_cache_dir).resolve() if not Path(self.argus_cache_dir).is_absolute() else Path(self.argus_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def primary_llm(self) -> tuple[str, str, str] | None:
        """Return (provider, api_key, model) for the highest-priority configured LLM (env-only)."""
        for provider, key, model in [
            ("anthropic", self.anthropic_api_key, self.anthropic_model),
            ("openai",    self.openai_api_key,   self.openai_model),
            ("deepseek",  self.deepseek_api_key, self.deepseek_model),
            ("qwen",      self.qwen_api_key,     self.qwen_model),
            ("nvidia",    self.nvidia_api_key,   self.nvidia_model),
        ]:
            if key:
                return provider, key, model
        if self.ollama_host:
            return "ollama", self.ollama_host, self.ollama_model
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
