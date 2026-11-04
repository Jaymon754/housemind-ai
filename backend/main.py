"""HouseMind AI FastAPI application entry point.

Run from the repository root:
    .venv/bin/uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import agent, dashboard, investment, knowledge, reports, system, valuation, vision
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.rag.engine import get_rag_service
from backend.app.services.model_service import get_model_service
from backend.app.services.vision_service import get_vision_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("housemind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HouseMind AI …")
    init_db()
    get_model_service()
    rag = get_rag_service()
    get_vision_service()
    logger.info("Model, RAG (%s, %s chunks) and vision services ready", rag.backend, len(rag.chunks))
    yield
    logger.info("HouseMind AI stopped")


app = FastAPI(
    title="HouseMind AI API",
    version=settings.app_version,
    description="AI 驱动的智能房产估值与投资决策平台 — 真实数据、真实模型、可解释的 Agent。",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - started) * 1000:.1f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


for router in [
    system.router,
    dashboard.router,
    valuation.router,
    investment.router,
    agent.router,
    knowledge.router,
    vision.router,
    reports.router,
]:
    app.include_router(router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务暂时不可用，请稍后重试。", "kind": type(exc).__name__})


@app.get("/api")
def api_root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
        "mode": "deepseek" if settings.llm_enabled else "local",
    }


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi.json")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
