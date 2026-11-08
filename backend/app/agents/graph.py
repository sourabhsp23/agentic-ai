"""InsightPilot multi-agent workflow (LangGraph).

retrieve_context -> planner --(not data)--> finalize
                       |
                       v
               +--> sql_agent <--(retry on SQL error, self-correction)
               |       |
               |       +--> analyst ----+      (parallel fan-out)
               |       +--> visualizer -+
               |                        v
               +----(revise)------- critic --(approve)--> finalize
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

import duckdb
from langgraph.graph import END, START, StateGraph

from app.agents import prompts as P
from app.agents.charts import build_chart
from app.agents.state import AgentState
from app.config import Settings
from app.llm.base import LLMClient, LLMResult
from app.observability.metrics import AGENT_NODE_LATENCY
from app.rag.store import InMemoryVectorStore, PgVectorStore
from app.tools.sql_engine import QueryResult, SQLEngine
from app.tools.sql_guard import UnsafeSQLError

log = logging.getLogger(__name__)


@dataclass
class AgentDeps:
    llm: LLMClient
    engine: SQLEngine
    store: InMemoryVectorStore | PgVectorStore
    settings: Settings


def _usage(node: str, r: LLMResult) -> dict[str, Any]:
    return {"node": node, "model": r.model, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens}


def traced(name: str) -> Callable:
    """Time a node, record a Prometheus metric and append a trace event."""

    def decorator(fn: Callable[[AgentState], dict]) -> Callable[[AgentState], dict]:
        @wraps(fn)
        def wrapper(state: AgentState) -> dict:
            start = time.perf_counter()
            update = fn(state)
            elapsed = time.perf_counter() - start
            AGENT_NODE_LATENCY.labels(name).observe(elapsed)
            event = {"node": name, "ms": round(elapsed * 1000, 1), "summary": update.pop("_summary", "")}
            log.info("node=%s %.0fms %s", name, elapsed * 1000, event["summary"], extra={"node": name})
            update["trace"] = [event]
            return update

        return wrapper

    return decorator


def _context_block(state: AgentState) -> str:
    ctx = state.get("context") or []
    return "\n\n".join(f"[{c['source']}]\n{c['content']}" for c in ctx) or "(none)"


def build_graph(deps: AgentDeps):
    llm, engine, settings = deps.llm, deps.engine, deps.settings

    # ---------------------------------------------------------------- nodes
    @traced("retrieve_context")
    def retrieve_context(state: AgentState) -> dict:
        schema = engine.schema_prompt(state["dataset"])
        try:
            chunks = deps.store.search(state["question"], settings.rag_top_k)
        except Exception:
            # Business context improves answers but isn't required: continue without it.
            log.warning("Knowledge search failed; continuing without business context", exc_info=True)
            return {"schema": schema, "context": [], "_summary": "Loaded schema; knowledge base unavailable"}
        context = [{"source": c.source, "content": c.content, "score": round(c.score, 3)} for c in chunks]
        sources = ", ".join(sorted({c["source"] for c in context})) or "none"
        return {"schema": schema, "context": context, "_summary": f"Loaded schema; context from {sources}"}

    @traced("planner")
    def planner(state: AgentState) -> dict:
        prompt = (
            f"### Question\n{state['question']}\n\n### Schema\n{state['schema']}\n\n"
            f"### Business context\n{_context_block(state)}"
        )
        r = llm.structured(
            system=P.PLANNER_SYSTEM,
            prompt=prompt,
            tool_name="submit_plan",
            tool_description="Submit the analysis plan.",
            schema=P.PLAN_SCHEMA,
        )
        plan = r.data
        update: dict[str, Any] = {"plan": plan, "usage": [_usage("planner", r)]}
        if plan.get("intent") != "data_query":
            update["final_answer"] = plan.get("direct_answer") or plan.get("reasoning", "")
        update["_summary"] = f"intent={plan.get('intent')}; {len(plan.get('steps', []))} steps"
        return update

    @traced("sql_agent")
    def sql_agent(state: AgentState) -> dict:
        attempts = state.get("sql_attempts", 0) + 1
        prompt = (
            f"### Question\n{state['question']}\n\n### Schema\n{state['schema']}\n\n"
            f"### Business context\n{_context_block(state)}\n\n"
            f"### Plan\n" + "\n".join(f"- {s}" for s in state["plan"].get("steps", []))
        )
        if state.get("sql_error"):
            prompt += (
                f"\n\n### Previous attempt failed\nSQL:\n{state.get('sql')}\nError:\n{state['sql_error']}"
            )
        if state.get("feedback"):
            prompt += (
                f"\n\n### Reviewer feedback on previous answer\n{state['feedback']}"
                f"\nPrevious SQL:\n{state.get('sql')}"
            )
        r = llm.structured(
            system=P.SQL_SYSTEM,
            prompt=prompt,
            tool_name="submit_sql",
            tool_description="Submit the SQL query.",
            schema=P.SQL_SCHEMA,
        )
        sql = r.data.get("sql", "")
        update: dict[str, Any] = {"sql": sql, "sql_attempts": attempts, "usage": [_usage("sql_agent", r)]}
        try:
            res: QueryResult = engine.run(state["dataset"], sql)
        except (UnsafeSQLError, duckdb.Error) as exc:
            update |= {
                "sql_error": str(exc)[:1000],
                "result": None,
                "_summary": f"attempt {attempts} failed: {str(exc)[:120]}",
            }
            return update
        update |= {
            "sql": res.sql,
            "sql_error": None,
            "result": {
                "columns": res.columns,
                "rows": res.rows,
                "truncated": res.truncated,
                "elapsed_ms": res.elapsed_ms,
            },
            "_summary": f"attempt {attempts} ok: {len(res.rows)} rows in {res.elapsed_ms}ms",
        }
        return update

    @traced("analyst")
    def analyst(state: AgentState) -> dict:
        res = state["result"] or {}
        table = QueryResult(
            state["sql"], res.get("columns", []), res.get("rows", []), res.get("truncated", False), 0
        ).to_markdown()
        prompt = (
            f"### Question\n{state['question']}\n\n### Business context\n{_context_block(state)}\n\n"
            f"### SQL\n{state['sql']}\n\n### Query results\n{table}"
        )
        r = llm.structured(
            system=P.ANALYST_SYSTEM,
            prompt=prompt,
            tool_name="submit_analysis",
            tool_description="Submit the answer and insights.",
            schema=P.ANALYSIS_SCHEMA,
        )
        return {
            "analysis": r.data,
            "usage": [_usage("analyst", r)],
            "_summary": f"{len(r.data.get('key_insights', []))} insights",
        }

    @traced("visualizer")
    def visualizer(state: AgentState) -> dict:
        res = state["result"] or {}
        cols, rows = res.get("columns", []), res.get("rows", [])
        if not state["plan"].get("needs_chart") or len(rows) < 2 or len(cols) < 2:
            return {"chart": None, "_summary": "no chart needed"}
        preview = QueryResult("", cols, rows, False, 0).to_markdown(limit=8)
        prompt = (
            f"### Question\n{state['question']}\n\n### Result columns\n{cols}\n\n### Query results\n{preview}"
        )
        r = llm.structured(
            system=P.VIZ_SYSTEM,
            prompt=prompt,
            tool_name="submit_chart",
            tool_description="Submit the chart specification.",
            schema=P.CHART_SCHEMA,
        )
        chart = build_chart(r.data, cols, rows, state["question"])
        return {
            "chart": chart,
            "usage": [_usage("visualizer", r)],
            "_summary": f"{chart['type']} chart" if chart else "no suitable chart",
        }

    @traced("critic")
    def critic(state: AgentState) -> dict:
        res = state["result"] or {}
        table = QueryResult(
            state["sql"], res.get("columns", []), res.get("rows", []), res.get("truncated", False), 0
        ).to_markdown()
        prompt = (
            f"### Question\n{state['question']}\n\n### Business context\n{_context_block(state)}\n\n"
            f"### SQL\n{state['sql']}\n\n### Query results\n{table}\n\n"
            f"### Proposed answer\n{state['analysis'].get('answer', '')}"
        )
        r = llm.structured(
            system=P.CRITIC_SYSTEM,
            prompt=prompt,
            tool_name="submit_review",
            tool_description="Submit the review verdict.",
            schema=P.REVIEW_SCHEMA,
        )
        review = r.data
        update: dict[str, Any] = {"review": review, "usage": [_usage("critic", r)]}
        if review.get("verdict") == "revise" and state.get("revisions", 0) < settings.max_revisions:
            update |= {
                "revisions": state.get("revisions", 0) + 1,
                "feedback": review.get("feedback"),
                "sql_attempts": 0,
                "sql_error": None,
            }
        update["_summary"] = f"verdict={review.get('verdict')} score={review.get('score')}"
        return update

    @traced("finalize")
    def finalize(state: AgentState) -> dict:
        plan = state.get("plan") or {}
        if plan and plan.get("intent") != "data_query":
            return {"status": "completed", "_summary": "answered directly"}
        if state.get("result") is None:
            msg = (
                f"I couldn't build a working query after {state.get('sql_attempts', 0)} attempts. "
                f"Last error: {state.get('sql_error')}"
            )
            return {
                "status": "failed",
                "error": state.get("sql_error"),
                "final_answer": msg,
                "_summary": "failed",
            }
        return {
            "status": "completed",
            "final_answer": state["analysis"].get("answer", ""),
            "_summary": "done",
        }

    # -------------------------------------------------------------- routing
    def after_planner(state: AgentState) -> str:
        return "sql_agent" if state["plan"].get("intent") == "data_query" else "finalize"

    def after_sql(state: AgentState) -> str | list[str]:
        if state.get("result") is not None:
            return ["analyst", "visualizer"]  # parallel fan-out
        if state.get("sql_attempts", 0) < settings.max_sql_attempts:
            return "sql_agent"  # self-correction loop
        return "finalize"

    def after_critic(state: AgentState) -> str:
        # critic set fresh feedback + reset attempts => go round again
        if state["review"].get("verdict") == "revise" and state.get("sql_attempts", 0) == 0:
            return "sql_agent"
        return "finalize"

    # ---------------------------------------------------------------- graph
    g = StateGraph(AgentState)
    for name, fn in [
        ("retrieve_context", retrieve_context),
        ("planner", planner),
        ("sql_agent", sql_agent),
        ("analyst", analyst),
        ("visualizer", visualizer),
        ("critic", critic),
        ("finalize", finalize),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "retrieve_context")
    g.add_edge("retrieve_context", "planner")
    g.add_conditional_edges("planner", after_planner, ["sql_agent", "finalize"])
    g.add_conditional_edges("sql_agent", after_sql, ["analyst", "visualizer", "sql_agent", "finalize"])
    g.add_edge(["analyst", "visualizer"], "critic")  # join: wait for both branches
    g.add_conditional_edges("critic", after_critic, ["sql_agent", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()
