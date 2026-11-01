from fastapi import FastAPI

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
