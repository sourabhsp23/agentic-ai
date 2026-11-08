"""Validate the Visualization Agent's chart choice, with deterministic fallbacks.

LLMs occasionally hallucinate column names; we never trust them blindly.
"""

import re
from typing import Any

_TIME_NAME = re.compile(r"(date|day|week|month|year|quarter|time|period)", re.I)
_TIME_VALUE = re.compile(r"^\d{4}(-\d{2})?(-\d{2})?")
_CHART_TYPES = {"bar", "line", "pie", "scatter"}
_MAX_POINTS = 100


def _is_id(name: str) -> bool:
    return name.lower() == "id" or name.lower().endswith("_id")


def _is_numeric(rows: list[list[Any]], idx: int) -> bool:
    vals = [r[idx] for r in rows if r[idx] is not None]
    return bool(vals) and all(isinstance(v, int | float) and not isinstance(v, bool) for v in vals)


def _is_time(name: str, rows: list[list[Any]], idx: int) -> bool:
    sample = next((r[idx] for r in rows if r[idx] is not None), None)
    return bool(_TIME_NAME.search(name)) or (isinstance(sample, str) and bool(_TIME_VALUE.match(sample)))


def _heuristic(cols: list[str], rows: list[list[Any]]) -> tuple[str, str, str] | None:
    ids = {i for i in range(len(cols)) if _is_id(cols[i])}
    numeric = [i for i in range(len(cols)) if _is_numeric(rows, i) and i not in ids]
    categorical = [i for i in range(len(cols)) if i not in numeric and i not in ids]
    if categorical and numeric:
        x = categorical[0]
        kind = "line" if _is_time(cols[x], rows, x) else "bar"
        return kind, cols[x], cols[numeric[0]]
    if len(numeric) >= 2:
        x = numeric[0]
        kind = "line" if _is_time(cols[x], rows, x) else "scatter"
        return kind, cols[x], cols[numeric[1]]
    return None


def build_chart(choice: dict[str, Any], cols: list[str], rows: list[list[Any]], question: str) -> dict | None:
    kind = choice.get("chart_type", "auto")
    if kind == "none":
        return None
    x, y = choice.get("x"), choice.get("y")
    valid = (
        kind in _CHART_TYPES
        and x in cols
        and y in cols
        and not _is_id(y)
        and _is_numeric(rows, cols.index(y))
    )
    if not valid:
        picked = _heuristic(cols, rows)
        if not picked:
            return None
        kind, x, y = picked
    if kind == "pie" and len(rows) > 4:
        kind = "bar"
    xi, yi = cols.index(x), cols.index(y)
    data = rows[:_MAX_POINTS]
    return {
        "type": kind,
        "x": x,
        "y": y,
        "title": choice.get("title") or question[:80],
        "labels": [r[xi] for r in data],
        "values": [r[yi] for r in data],
    }
