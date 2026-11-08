"""DuckDB analytics engine: loads each dataset's CSVs into an isolated in-memory DB.

After loading, external access is disabled and configuration locked, so even a
malicious query cannot read files, hit the network, or re-enable either.
"""

import datetime as dt
import decimal
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

from app.observability.metrics import SQL_QUERIES
from app.tools.sql_guard import validate_sql
from app.tools.storage import LocalStorage, S3Storage

log = logging.getLogger(__name__)


@dataclass
class TableInfo:
    name: str
    row_count: int
    columns: list[tuple[str, str]]
    sample_rows: list[list[Any]] = field(default_factory=list)


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool
    elapsed_ms: float

    def to_markdown(self, limit: int = 30) -> str:
        if not self.columns:
            return "(no columns)"
        lines = [" | ".join(self.columns)]
        lines += [" | ".join(str(v) for v in row) for row in self.rows[:limit]]
        if len(self.rows) > limit:
            lines.append(f"... ({len(self.rows) - limit} more rows)")
        if self.truncated:
            lines.append("(result truncated by row limit)")
        return "\n".join(lines)


def _jsonable(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, dt.date | dt.datetime | dt.time):
        return value.isoformat()
    if isinstance(value, dt.timedelta):
        return str(value)
    if isinstance(value, uuid.UUID | bytes):
        return str(value)
    return value


class SQLEngine:
    def __init__(self, storage: LocalStorage | S3Storage, max_rows: int = 200) -> None:
        self.storage = storage
        self.max_rows = max_rows
        self._conns: dict[str, duckdb.DuckDBPyConnection] = {}
        self._lock = threading.Lock()

    # --- connection management -------------------------------------------
    def _load(self, dataset: str) -> duckdb.DuckDBPyConnection:
        folder: Path = self.storage.local_dir(dataset)
        con = duckdb.connect(":memory:")
        for csv in sorted(folder.glob("*.csv")):
            path = csv.resolve().as_posix().replace("'", "''")
            con.execute(f"CREATE TABLE \"{csv.stem}\" AS SELECT * FROM read_csv_auto('{path}')")
        con.execute("SET enable_external_access = false")
        con.execute("SET lock_configuration = true")
        log.info("Loaded dataset %s into DuckDB", dataset)
        return con

    def connection(self, dataset: str) -> duckdb.DuckDBPyConnection:
        with self._lock:
            if dataset not in self._conns:
                self._conns[dataset] = self._load(dataset)
            return self._conns[dataset]

    def invalidate(self, dataset: str) -> None:
        with self._lock:
            con = self._conns.pop(dataset, None)
        if con:
            con.close()

    # --- introspection ----------------------------------------------------
    def schema(self, dataset: str, sample_rows: int = 3) -> list[TableInfo]:
        cur = self.connection(dataset).cursor()
        tables = [r[0] for r in cur.execute("SHOW TABLES").fetchall()]
        infos = []
        for t in tables:
            cols = cur.execute(f'DESCRIBE "{t}"').fetchall()
            count = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            sample = cur.execute(f'SELECT * FROM "{t}" LIMIT {sample_rows}').fetchall()
            infos.append(
                TableInfo(
                    name=t,
                    row_count=count,
                    columns=[(c[0], c[1]) for c in cols],
                    sample_rows=[[_jsonable(v) for v in r] for r in sample],
                )
            )
        return infos

    def schema_prompt(self, dataset: str) -> str:
        """Compact schema description for LLM prompts."""
        parts = []
        for t in self.schema(dataset):
            cols = ", ".join(f"{n} {ty}" for n, ty in t.columns)
            parts.append(f"TABLE {t.name} ({cols})  -- {t.row_count} rows")
            for row in t.sample_rows:
                parts.append(f"  sample: {row}")
        return "\n".join(parts)

    # --- execution --------------------------------------------------------
    def run(self, dataset: str, sql: str) -> QueryResult:
        safe_sql = validate_sql(sql)
        cur = self.connection(dataset).cursor()
        start = time.perf_counter()
        try:
            cur.execute(safe_sql)
            rows = cur.fetchmany(self.max_rows + 1)
        except duckdb.Error:
            SQL_QUERIES.labels("error").inc()
            raise
        SQL_QUERIES.labels("ok").inc()
        columns = [d[0] for d in cur.description or []]
        truncated = len(rows) > self.max_rows
        return QueryResult(
            sql=safe_sql,
            columns=columns,
            rows=[[_jsonable(v) for v in r] for r in rows[: self.max_rows]],
            truncated=truncated,
            elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
        )
