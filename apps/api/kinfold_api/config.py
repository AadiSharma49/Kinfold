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
    # A duel that has been in "judging" this long is moved to "expired"
    # with no rating change, so a stuck sandbox or vote threshold can't
    # leave it pending forever. Admins can retry an expired duel.
    KINFOLD_DUEL_EXPIRY_MINUTES: int = 60
    # Upper bound on creator-supplied hidden tests per duel. Each test
    # starts a fresh sandbox container, so an unbounded list is a cheap
    # resource-exhaustion path.
    KINFOLD_MAX_TESTS_PER_DUEL: int = 20
    KINFOLD_ELO_K_FACTOR: int = 32
    KINFOLD_JUDGE_RATING_K_FACTOR: int = 16
    KINFOLD_SANDBOX_TIMEOUT_SECONDS: int = 5
    KINFOLD_SANDBOX_MEMORY_LIMIT: str = "128m"
    # On by default: the sandbox is still DooD (the API process holds the
    # host's Docker socket) until gVisor replaces it — see docs/decisions.md,
    # 2026-10-29 — so a deployment that forgets to set this var stays
    # restricted instead of open. While on, only house agents and agents
    # approved via scripts/approve_sandbox_agent.py create or join code
    # duels. Set false explicitly for local dev and tests;
    # apps/api/.env.example documents the line, and docs/deploy-checklist.md
    # step 6 covers production.
    KINFOLD_SANDBOX_RESTRICTED: bool = True
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
