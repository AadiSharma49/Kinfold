from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kinfold_api.config import get_settings
from kinfold_api.logging_config import configure_logging
from kinfold_api.middleware import RequestContextMiddleware
from kinfold_api.routers import (
    admin,
    agents,
    auth,
    data_stats,
    duels,
    events,
    health,
    keys,
    owners,
    reports,
)

configure_logging()

app = FastAPI(title="Kinfold API", version="0.1.0")

app.add_middleware(RequestContextMiddleware)

settings = get_settings()
# Only the website is allowed to make browser calls. Agents and the MCP
# server are not browsers, so they are unaffected. No cookies/credentials
# are used — keys travel in the Authorization header — so credentials
# stay off. Localhost stays listed for local development. Added after
# RequestContext so CORS stays outermost and preflights don't burn rate
# limit or need application processing.
_allowed_origins = {
    settings.KINFOLD_WEB_URL.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    expose_headers=["X-Request-Id"],
    max_age=600,
)

app.include_router(health.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(owners.router, prefix="/v1")
app.include_router(keys.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(duels.router, prefix="/v1")
app.include_router(events.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(data_stats.router, prefix="/v1")
