"""Static safety checks for LLM-generated SQL (defence in depth).

Layer 1 (here): parse with sqlglot -> single read-only SELECT, no file/network functions.
Layer 2 (sql_engine): DuckDB runs with external access disabled + config locked.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

_READ_ONLY_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)

_FORBIDDEN_NODE_NAMES = (
    "Insert",
    "Update",
    "Delete",
    "Create",
    "Drop",
    "Alter",
    "Command",
    "Merge",
    "TruncateTable",
    "Copy",
    "Attach",
    "Detach",
    "Pragma",
    "Set",
    "Use",
)
_FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NODE_NAMES if hasattr(exp, n))

_FORBIDDEN_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "read_json",
    "read_json_auto",
    "read_text",
    "read_blob",
    "glob",
    "parquet_scan",
    "csv_scan",
    "sniff_csv",
    "query",
    "query_table",
    "getenv",
    "current_setting",
}


class UnsafeSQLError(ValueError):
    pass


def validate_sql(sql: str) -> str:
    """Return normalised SQL if safe, else raise UnsafeSQLError with a helpful message."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise UnsafeSQLError("Empty SQL.")
    try:
        statements = sqlglot.parse(cleaned, read="duckdb")
    except ParseError as exc:
        raise UnsafeSQLError(f"SQL syntax error: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSQLError("Exactly one SQL statement is allowed.")
    root = statements[0]

    if not isinstance(root, _READ_ONLY_ROOTS):
        raise UnsafeSQLError(f"Only SELECT queries are allowed (got {root.key.upper()}).")

    for node in root.walk():
        if _FORBIDDEN_NODES and isinstance(node, _FORBIDDEN_NODES):
            raise UnsafeSQLError(f"Forbidden operation: {node.key.upper()}.")
        if isinstance(node, exp.Func):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in _FORBIDDEN_FUNCTIONS:
                raise UnsafeSQLError(f"Function '{name}' is not allowed.")
    return cleaned
