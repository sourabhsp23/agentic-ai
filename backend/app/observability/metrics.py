"""Prometheus metrics exposed on /metrics (scraped by Prometheus / CloudWatch agent / AMP)."""

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("insightpilot_http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_LATENCY = Histogram("insightpilot_http_request_seconds", "HTTP request latency", ["method", "path"])
AGENT_RUNS = Counter("insightpilot_agent_runs_total", "Agent runs", ["status"])
AGENT_NODE_LATENCY = Histogram(
    "insightpilot_agent_node_seconds",
    "Latency of each agent node",
    ["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 40),
)
LLM_TOKENS = Counter("insightpilot_llm_tokens_total", "LLM tokens used", ["model", "kind"])
LLM_CALLS = Counter("insightpilot_llm_calls_total", "LLM calls", ["model", "status"])
SQL_QUERIES = Counter("insightpilot_sql_queries_total", "SQL queries executed", ["status"])
