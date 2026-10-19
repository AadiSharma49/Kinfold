from fastapi import FastAPI

from kinfold_api.routers import agents, events, health, keys, owners

app = FastAPI(title="Kinfold API", version="0.1.0")

app.include_router(health.router, prefix="/v1")
app.include_router(owners.router, prefix="/v1")
app.include_router(keys.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(events.router, prefix="/v1")
