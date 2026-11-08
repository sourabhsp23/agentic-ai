"""Runs the agent graph, streams step events, and persists every run for audit/history."""

import logging
import time
import uuid
from collections.abc import Iterator
from typing import Any

from app.core.container import Container
from app.db.models import AgentRun
from app.llm.base import estimate_cost
from app.observability.metrics import AGENT_RUNS

log = logging.getLogger(__name__)

_APPEND_KEYS = {"trace", "usage"}


def _merge(state: dict[str, Any], update: dict[str, Any]) -> None:
    for k, v in update.items():
        if k in _APPEND_KEYS:
            state.setdefault(k, []).extend(v)
        else:
            state[k] = v


def _summarise(run_id: str, state: dict[str, Any], latency_ms: float) -> dict[str, Any]:
    usage = state.get("usage", [])
    in_tok = sum(u["input_tokens"] for u in usage)
    out_tok = sum(u["output_tokens"] for u in usage)
    model = usage[0]["model"] if usage else None
    result = state.get("result") or {}
    analysis = state.get("analysis") or {}
    return {
        "run_id": run_id,
        "status": state.get("status", "failed"),
        "answer": state.get("final_answer", ""),
        "insights": analysis.get("key_insights", []),
        "follow_ups": analysis.get("follow_up_questions", []),
        "sql": state.get("sql"),
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "truncated": result.get("truncated", False),
        "chart": state.get("chart"),
        "plan": state.get("plan"),
        "review": state.get("review"),
        "sources": sorted({c["source"] for c in state.get("context", [])}),
        "trace": state.get("trace", []),
        "usage": {
            "model": model,
            "llm_calls": len(usage),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": round(estimate_cost(model or "", in_tok, out_tok), 6),
        },
        "latency_ms": round(latency_ms, 1),
        "error": state.get("error"),
    }


class AgentService:
    def __init__(self, container: Container) -> None:
        self.c = container

    def stream(self, dataset: str, question: str) -> Iterator[dict[str, Any]]:
        run_id = str(uuid.uuid4())
        start = time.perf_counter()
        yield {"type": "start", "run_id": run_id}

        state: dict[str, Any] = {"run_id": run_id, "dataset": dataset, "question": question}
        try:
            for chunk in self.c.graph.stream(dict(state), stream_mode="updates"):
                for update in chunk.values():
                    if not update:
                        continue
                    _merge(state, update)
                    for ev in update.get("trace", []):
                        yield {"type": "step", **ev}
        except Exception as exc:  # surface any unexpected failure to the client
            log.exception("Agent run %s crashed", run_id)
            state |= {
                "status": "failed",
                "error": str(exc),
                "final_answer": "Something went wrong while running the agents.",
            }

        summary = _summarise(run_id, state, (time.perf_counter() - start) * 1000)
        AGENT_RUNS.labels(summary["status"]).inc()
        self._persist(dataset, question, summary)
        yield {"type": "final", "result": summary}

    def run(self, dataset: str, question: str) -> dict[str, Any]:
        final: dict[str, Any] = {}
        for event in self.stream(dataset, question):
            if event["type"] == "final":
                final = event["result"]
        return final

    def _persist(self, dataset: str, question: str, s: dict[str, Any]) -> None:
        try:
            with self.c.sessions() as db:
                db.add(
                    AgentRun(
                        id=s["run_id"],
                        dataset=dataset,
                        question=question,
                        status=s["status"],
                        answer=s["answer"],
                        sql=s["sql"],
                        chart=s["chart"],
                        trace=s["trace"],
                        error=s["error"],
                        model=s["usage"]["model"],
                        input_tokens=s["usage"]["input_tokens"],
                        output_tokens=s["usage"]["output_tokens"],
                        cost_usd=s["usage"]["cost_usd"],
                        latency_ms=s["latency_ms"],
                    )
                )
                db.commit()
        except Exception:
            log.exception("Failed to persist run %s", s["run_id"])
