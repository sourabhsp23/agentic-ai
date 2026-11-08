import json


def test_health_and_ready(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200
    assert "insightpilot_http_requests_total" in client.get("/metrics").text


def test_datasets_and_schema(client):
    names = [d["name"] for d in client.get("/api/datasets").json()]
    assert "ecommerce" in names
    tables = {t["name"] for t in client.get("/api/datasets/ecommerce/schema").json()}
    assert "orders" in tables
    assert client.get("/api/datasets/missing/schema").status_code == 404


def test_ask_persists_run(client):
    r = client.post("/api/ask", json={"dataset": "ecommerce", "question": "How many customers?"})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "completed"
    assert body["rows"][0][0] == 800
    run = client.get(f"/api/runs/{body['run_id']}").json()
    assert run["question"] == "How many customers?"


def test_ask_stream_emits_events(client):
    with client.stream(
        "POST", "/api/ask/stream", json={"dataset": "ecommerce", "question": "Show products"}
    ) as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert types[0] == "start" and types[-1] == "final" and "step" in types


def test_validation_and_unknown_dataset(client):
    assert client.post("/api/ask", json={"dataset": "../etc", "question": "x?"}).status_code == 422
    assert client.post("/api/ask", json={"dataset": "nope", "question": "hi?"}).status_code == 404
