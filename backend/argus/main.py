"""Argus FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .routes import analysis, committee, market, screener, settings as settings_route, system, watchlist, ws
from .storage import init_db
from .utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    s = get_settings()
    primary = s.primary_llm()
    if primary:
        logger.info(f"Argus v{__version__} starting — LLM: {primary[0]} ({primary[2]})")
    else:
        logger.info(f"Argus v{__version__} starting — LLM: mock (no key configured)")
    yield


app = FastAPI(
    title="Argus",
    description="Multi-agent multi-market stock intelligence",
    version=__version__,
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(market.router)
app.include_router(analysis.router)
app.include_router(committee.router)
app.include_router(screener.router)
app.include_router(watchlist.router)
app.include_router(settings_route.router)
app.include_router(ws.router)


# Serve built frontend if present (for production single-binary deploy)
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="static")


@app.get("/api")
def api_root():
    return {
        "name": "Argus",
        "version": __version__,
        "docs": "/docs",
        "endpoints": [
            "/api/system/health",
            "/api/system/capabilities",
            "/api/market/search?q=",
            "/api/market/quote/{symbol}",
            "/api/market/history/{symbol}",
            "/api/analysis/indicators/{symbol}",
            "/api/analysis/fundamentals/{symbol}",
            "/api/committee/stream/{symbol}",
            "/api/screener/run",
            "/api/screener/preset/{name}",
            "/api/watchlist",
            "/ws/quotes",
        ],
    }
