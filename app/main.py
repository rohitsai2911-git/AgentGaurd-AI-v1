from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes import health
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, request_id_var
from app.db.session import SessionLocal, init_db

logger = logging.getLogger(__name__)

DESCRIPTION = """
Deterministic quality and reliability testing for AI agents.

**Five evaluation dimensions** — accuracy, hallucination risk, safety,
instruction compliance, consistency. Every score names the rule that produced it.

**Orchestration** — test suites, suite execution, failure classification,
analytics, trend tracking, run comparison and JSON export.

**Honesty contract** — findings are labelled `verified` (provable against the test
case's grounding source) or `risk` (a heuristic indicator requiring human review).
Heuristic detection cannot find every hallucination; the absence of findings is not
proof of correctness.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    logger.info("%s %s started", settings.name, settings.version)

    if settings.auto_seed:
        from app.services import seed as seed_service

        with SessionLocal() as session:
            seed_service.load_seed(session)
        logger.info("Auto-seeded sample data")

    yield
    logger.info("%s shutting down", settings.name)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.name,
        version=settings.version,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        logger.warning(
            "%s %s -> %s (%s)", request.method, request.url.path, exc.code, exc.message
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.code, "message": exc.message, "details": exc.details},
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in err.get("loc", [])[1:]) or "body",
                "message": err.get("msg", "invalid value"),
                "type": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        logger.warning("Validation error on %s: %s", request.url.path, details)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "Request payload failed validation.",
                    "details": {"fields": details},
                },
                "request_id": request_id_var.get(),
            },
        )

    app.include_router(health.router)
    app.include_router(api_router)

    @app.get("/", tags=["health"], summary="API index")
    def index():
        return {
            "name": settings.name,
            "version": settings.version,
            "stage": "1-2 (backend complete, frontend pending)",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }

    return app


app = create_app()