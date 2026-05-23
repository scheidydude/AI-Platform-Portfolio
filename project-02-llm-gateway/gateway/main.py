from __future__ import annotations
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .backends import create_backend
from .config import load_config
from .observability import logger
from .ratelimit import RateLimiter
from .routes import admin, chat, models
from .state.sqlite import SqliteQuotaStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = os.environ.get("GATEWAY_CONFIG", "gateway.yaml")
    db_path = os.environ.get("GATEWAY_DB", "gateway.db")

    config = load_config(config_path)
    store = SqliteQuotaStore(db_path)
    await store.init()

    initialized_backends = {
        name: create_backend(backend_cfg, name)
        for name, backend_cfg in config.backends.items()
    }

    app.state.config = config
    app.state.store = store
    app.state.backends = initialized_backends
    app.state.rate_limiter = RateLimiter()

    logger.info({"event": "startup", "backends": list(initialized_backends), "teams": list(config.teams)})
    yield

    for backend in initialized_backends.values():
        await backend.close()
    logger.info({"event": "shutdown"})


app = FastAPI(title="LLM Gateway", version="0.1.0", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(models.router)
app.include_router(admin.router)


@app.get("/healthz")
async def health() -> dict:
    return {"ok": True}
