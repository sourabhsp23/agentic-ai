"""FastAPI entrypoint.  Run locally:  uvicorn app.main:app --reload"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.core.container import build_container
from app.observability.logging import request_id_ctx, setup_logging
from app.observability.metrics import HTTP_LATENCY, HTTP_REQUESTS

settings = get_settings()
setup_logging(settings.log_level, settings.log_json)
log = logging.getLogger("insightpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_container(settings)
    log.info("%s v%s started (env=%s)", settings.app_name, __version__, settings.app_env)
    yield
    app.state.container.db_engine.dispose()


app = FastAPI(
    title="InsightPilot API",
    description="Autonomous multi-agent data analyst powered by Amazon Bedrock + LangGraph",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)


@app.middleware("http")
async def observe(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    token = request_id_ctx.set(rid)
    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")  # template path => low-cardinality labels
    HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
    HTTP_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    response.headers["x-request-id"] = rid
    return response


@app.get("/healthz", tags=["ops"])
def healthz() -> dict:
    """Liveness probe: the process is up."""
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])
def readyz(request: Request, response: Response) -> dict:
    """Readiness probe: dependencies (database) are reachable."""
    try:
        with request.app.state.container.db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        response.status_code = 503
        return {"status": "not-ready", "error": str(exc)}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)
