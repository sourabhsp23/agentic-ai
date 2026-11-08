import json
import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from app import __version__
from app.api.schemas import AskRequest, DatasetOut, RunOut, TableSchema
from app.config import get_settings
from app.core.container import Container
from app.core.service import AgentService
from app.db.models import AgentRun
from app.tools.storage import safe_dataset_name

log = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def get_container(request: Request) -> Container:
    return request.app.state.container


def require_api_key(request: Request) -> None:
    expected = get_settings().api_key
    if expected and request.headers.get("x-api-key") != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def _ensure_dataset(c: Container, name: str) -> None:
    try:
        c.sql_engine.connection(safe_dataset_name(name))
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/info")
def info() -> dict:
    s = get_settings()
    return {
        "name": s.app_name,
        "version": __version__,
        "env": s.app_env,
        "git_sha": os.getenv("GIT_SHA", "dev"),  # injected by CI/CD at build time
        "llm_provider": s.llm_provider,
        "model": s.bedrock_model_id if s.llm_provider == "bedrock" else "fake",
        "storage": s.storage_backend,
    }


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(c: Container = Depends(get_container)):
    return [DatasetOut(name=d.name, files=d.files) for d in c.storage.list_datasets()]


@router.get("/datasets/{name}/schema", response_model=list[TableSchema])
def dataset_schema(name: str, c: Container = Depends(get_container)):
    _ensure_dataset(c, name)
    return [
        TableSchema(name=t.name, row_count=t.row_count, columns=t.columns)
        for t in c.sql_engine.schema(name, sample_rows=0)
    ]


@router.post("/datasets/{name}/upload", status_code=201)
async def upload(name: str, file: UploadFile = File(...), c: Container = Depends(get_container)):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 20MB).")
    try:
        await run_in_threadpool(c.storage.save, name, file.filename or "upload.csv", content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    c.sql_engine.invalidate(name)
    _ensure_dataset(c, name)  # validates the CSV actually loads
    return {"dataset": name, "file": file.filename, "bytes": len(content)}


@router.post("/ask")
async def ask(req: AskRequest, c: Container = Depends(get_container)):
    _ensure_dataset(c, req.dataset)
    return await run_in_threadpool(AgentService(c).run, req.dataset, req.question)


@router.post("/ask/stream")
async def ask_stream(req: AskRequest, c: Container = Depends(get_container)):
    """Server-Sent Events: one `step` event per agent node, then a `final` event."""
    _ensure_dataset(c, req.dataset)

    async def events():
        stream = AgentService(c).stream(req.dataset, req.question)
        async for ev in iterate_in_threadpool(stream):
            yield f"event: {ev['type']}\ndata: {json.dumps(ev, default=str)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # X-Accel-Buffering disables nginx buffering so events arrive live.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _run_out(r: AgentRun) -> RunOut:
    return RunOut(
        id=r.id,
        created_at=r.created_at.isoformat(),
        dataset=r.dataset,
        question=r.question,
        status=r.status,
        answer=r.answer,
        sql=r.sql,
        chart=r.chart,
        trace=r.trace,
        model=r.model,
        input_tokens=r.input_tokens,
        output_tokens=r.output_tokens,
        cost_usd=r.cost_usd,
        latency_ms=r.latency_ms,
    )


@router.get("/runs", response_model=list[RunOut])
def list_runs(limit: int = 20, c: Container = Depends(get_container)):
    with c.sessions() as db:
        query = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(min(limit, 100))
        return [_run_out(r) for r in db.scalars(query)]


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, c: Container = Depends(get_container)):
    with c.sessions() as db:
        run = db.get(AgentRun, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        return _run_out(run)


@router.post("/knowledge/reindex")
def reindex(c: Container = Depends(get_container)) -> dict:
    return {"chunks_indexed": c.reindex_knowledge()}
