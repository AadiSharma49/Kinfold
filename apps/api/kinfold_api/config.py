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
    # A real planning number, not a derived ML requirement — a reasonable
    # starting target for a first small-scale DPO pipeline test. See
    # docs/decisions.md, 2026-11-01.
    KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS: int = 500
    # Per-IP limit for routes with no API key at all — every unauthenticated
    # route gets this via main.py's middleware (defense in depth; an
    # authenticated route is already covered by its own, separate per-key
    # limit on top of this). dev-signup doesn't get its own stricter limit:
    # it's already gated off entirely in production by KINFOLD_DEV_SIGNUP
    # (404s when false), so the real abuse surface this limit protects is
    # only a misconfigured deployment — the general limit is enough for
    # that and doesn't fight test suites that legitimately call dev-signup
    # many times per test run. See docs/security.md.
    KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE: int = 120
    # Comma-separated IPs/CIDR ranges allowed to set X-Forwarded-For and be
    # believed. Anyone else's X-Forwarded-For is ignored outright and the
    # real TCP peer address is used instead — otherwise any client could
    # spoof this header to dodge the rate limiter entirely by claiming a
    # different IP on every request. In docker-compose.prod.yml, set this
    # to Caddy's actual address on the compose network. Defaults to
    # loopback only, which is right for local dev (no proxy in front) and
    # wrong for production until set explicitly — see docs/security.md.
    KINFOLD_TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
