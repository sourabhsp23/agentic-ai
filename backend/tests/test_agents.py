"""End-to-end tests of the LangGraph workflow with scripted LLMs (no AWS needed)."""

from app.agents.graph import AgentDeps, build_graph
from app.config import get_settings
from app.llm.base import LLMResult
from app.llm.fake import FakeLLM
from app.rag.embeddings import HashingEmbedder
from app.rag.store import InMemoryVectorStore, ingest_directory
from app.tools.sql_engine import SQLEngine
from app.tools.storage import LocalStorage
from tests.conftest import ROOT


class ScriptedLLM(FakeLLM):
    """FakeLLM whose answers for given tools can be scripted as a queue."""

    def __init__(self, script: dict[str, list[dict]]):
        self.script = script
        self.calls: list[str] = []

    def structured(self, *, tool_name, prompt, **kw):
        self.calls.append(tool_name)
        queue = self.script.get(tool_name)
        if queue:
            return LLMResult(data=queue.pop(0), model="scripted", input_tokens=10, output_tokens=5)
        return super().structured(tool_name=tool_name, prompt=prompt, **kw)


def run(llm, question="How many orders are there?"):
    store = InMemoryVectorStore(HashingEmbedder(256))
    ingest_directory(store, ROOT / "knowledge")
    engine = SQLEngine(LocalStorage(ROOT / "sample_data"))
    graph = build_graph(AgentDeps(llm=llm, engine=engine, store=store, settings=get_settings()))
    return graph.invoke({"run_id": "t", "dataset": "ecommerce", "question": question})


def test_happy_path_fans_out_and_completes():
    llm = ScriptedLLM({})
    state = run(llm)
    assert state["status"] == "completed"
    assert state["result"]["columns"] == ["total"]
    nodes = [t["node"] for t in state["trace"]]
    assert {"analyst", "visualizer"} <= set(nodes) and nodes[-1] == "finalize"
    assert any("metrics.md" in c["source"] or "glossary.md" in c["source"] for c in state["context"])


def test_sql_self_correction_loop():
    llm = ScriptedLLM(
        {
            "submit_sql": [
                {"sql": "SELECT * FROM no_such_table", "explanation": "bad"},
                {"sql": "SELECT COUNT(*) AS n FROM orders", "explanation": "fixed"},
            ]
        }
    )
    state = run(llm)
    assert state["status"] == "completed" and state["sql_attempts"] == 2
    assert state["result"]["rows"][0][0] > 1000


def test_gives_up_after_max_attempts():
    bad = {"sql": "DROP TABLE orders", "explanation": "evil"}
    state = run(ScriptedLLM({"submit_sql": [bad, bad, bad]}))
    assert state["status"] == "failed"
    assert "Only SELECT" in state["sql_error"]


def test_critic_triggers_one_revision():
    llm = ScriptedLLM(
        {
            "submit_review": [
                {"verdict": "revise", "score": 0.3, "feedback": "Only count completed orders."},
                {"verdict": "approve", "score": 0.9, "feedback": "ok"},
            ]
        }
    )
    state = run(llm)
    assert state["revisions"] == 1 and state["status"] == "completed"
    assert llm.calls.count("submit_review") == 2


def test_conversational_short_circuits():
    llm = ScriptedLLM({})
    state = run(llm, question="hello there")
    assert state["status"] == "completed" and "InsightPilot" in state["final_answer"]
    assert "submit_sql" not in llm.calls
