from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    TEST_DATABASE_URL: str
    REDIS_URL: str
    KINFOLD_DEV_SIGNUP: bool = False
    KINFOLD_RATE_LIMIT_PER_MINUTE: int = 60
    KINFOLD_MAX_AGENTS_PER_OWNER: int = 5
    KINFOLD_MIN_VOTES_TO_RESOLVE: int = 3
    KINFOLD_ELO_K_FACTOR: int = 32
    KINFOLD_JUDGE_RATING_K_FACTOR: int = 16
    KINFOLD_SANDBOX_TIMEOUT_SECONDS: int = 5
    KINFOLD_SANDBOX_MEMORY_LIMIT: str = "128m"
    # Off by default (local dev, tests). Production should set this true
    # until the sandbox runs under gVisor instead of DooD — see
    # docs/decisions.md, 2026-10-29, and docs/deploy-checklist.md.
    KINFOLD_SANDBOX_RESTRICTED: bool = False
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    KINFOLD_PUBLIC_API_URL: str = "http://localhost:8000"
    KINFOLD_WEB_URL: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
