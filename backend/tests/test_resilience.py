"""Failure handling: network outages, bad credentials, and a broken knowledge base."""

from botocore.exceptions import ClientError, EndpointConnectionError

from app.agents.graph import AgentDeps, build_graph
from app.config import get_settings
from app.core.errors import describe_error
from app.llm.base import LLMError
from app.llm.fake import FakeLLM
from app.tools.sql_engine import SQLEngine
from app.tools.storage import LocalStorage
from tests.conftest import ROOT


def _client_error(code: str, message: str = "msg") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "Converse")


def test_network_error_is_explained_even_when_wrapped():
    try:
        try:
            raise EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com")
        except EndpointConnectionError as inner:
            raise LLMError("Bedrock call failed") from inner
    except LLMError as exc:
        assert "internet connection" in describe_error(exc)


def test_expired_key_and_access_denied_messages():
    assert "new API key" in describe_error(_client_error("ExpiredTokenException"))
    assert "model access" in describe_error(_client_error("AccessDeniedException", "no access"))
    assert "throttling" in describe_error(_client_error("ThrottlingException"))


class BrokenStore:
    def search(self, query, k):
        raise EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com")


def test_run_continues_when_knowledge_base_is_down():
    graph = build_graph(
        AgentDeps(
            llm=FakeLLM(),
            engine=SQLEngine(LocalStorage(ROOT / "sample_data")),
            store=BrokenStore(),
            settings=get_settings(),
        )
    )
    state = graph.invoke({"run_id": "t", "dataset": "ecommerce", "question": "How many orders are there?"})
    assert state["status"] == "completed"
    assert state["context"] == []
    assert "knowledge base unavailable" in state["trace"][0]["summary"]


def test_crashed_run_reports_actionable_message(client, monkeypatch):
    def boom(*args, **kwargs):
        raise LLMError("x") from _client_error("ExpiredTokenException")

    container = client.app.state.container
    monkeypatch.setattr(container.graph, "stream", boom)
    body = client.post("/api/ask", json={"dataset": "ecommerce", "question": "How many orders?"}).json()
    assert body["status"] == "failed"
    assert "new API key" in body["answer"]
