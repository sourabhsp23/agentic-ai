"""Deterministic offline LLM used for local dev without AWS, unit tests and CI.

It reads the same prompts the real model gets and produces plausible,
schema-valid outputs with simple heuristics. Zero cost, zero network.
"""

import re
from typing import Any

from app.llm.base import LLMResult

_GREETING = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|who are you)\b", re.I)


def _section(prompt: str, name: str) -> str:
    match = re.search(rf"### {name}\n(.*?)(?=\n### |\Z)", prompt, re.S)
    return match.group(1).strip() if match else ""


def _tables(prompt: str) -> list[str]:
    return re.findall(r"^TABLE (\w+)", _section(prompt, "Schema"), re.M)


class FakeLLM:
    model_id = "fake"

    def structured(
        self,
        *,
        system: str,
        prompt: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
    ) -> LLMResult:
        handler = getattr(self, f"_{tool_name}", None)
        data = handler(prompt) if handler else {}
        return LLMResult(data=data, model=self.model_id, input_tokens=len(prompt) // 4, output_tokens=50)

    # --- one handler per agent tool ---------------------------------------
    def _submit_plan(self, prompt: str) -> dict:
        question = _section(prompt, "Question")
        if _GREETING.match(question):
            return {
                "intent": "conversational",
                "reasoning": "Greeting / small talk.",
                "steps": [],
                "needs_chart": False,
                "direct_answer": "Hi! I'm InsightPilot. Ask me a question about your data.",
            }
        return {
            "intent": "data_query",
            "reasoning": "The question can be answered from the dataset with SQL.",
            "steps": ["Identify relevant tables", "Aggregate with SQL", "Summarise findings"],
            "needs_chart": True,
            "direct_answer": "",
        }

    def _submit_sql(self, prompt: str) -> dict:
        question = _section(prompt, "Question").lower()
        tables = _tables(prompt) or ["unknown_table"]
        table = next((t for t in tables if t.rstrip("s") in question), tables[0])
        if "how many" in question or "count" in question:
            sql = f"SELECT COUNT(*) AS total FROM {table}"
        else:
            sql = f"SELECT * FROM {table} LIMIT 10"
        return {"sql": sql, "explanation": f"Query the {table} table."}

    def _submit_analysis(self, prompt: str) -> dict:
        results = _section(prompt, "Query results")
        first = results.splitlines()[1] if len(results.splitlines()) > 1 else "no rows"
        return {
            "answer": f"Based on the query results, the first row is: {first}.",
            "key_insights": ["Result computed directly from the dataset (offline fake model)."],
            "follow_up_questions": ["Can you break this down by month?"],
        }

    def _submit_chart(self, prompt: str) -> dict:
        return {"chart_type": "auto", "x": "", "y": "", "title": "", "reason": "Let heuristics decide."}

    def _submit_review(self, prompt: str) -> dict:
        return {"verdict": "approve", "score": 0.9, "feedback": "Answer is grounded in the results."}
