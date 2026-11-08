import duckdb
import pytest

from app.agents.charts import build_chart
from app.tools.sql_engine import SQLEngine
from app.tools.storage import LocalStorage
from tests.conftest import ROOT


@pytest.fixture(scope="module")
def engine():
    return SQLEngine(LocalStorage(ROOT / "sample_data"), max_rows=50)


def test_schema_lists_all_tables(engine):
    names = {t.name for t in engine.schema("ecommerce")}
    assert names == {"customers", "orders", "order_items", "products"}


def test_run_truncates(engine):
    res = engine.run("ecommerce", "SELECT * FROM orders")
    assert len(res.rows) == 50 and res.truncated


def test_external_access_is_disabled(engine):
    # Even if the guard were bypassed, DuckDB itself refuses file access.
    con = engine.connection("ecommerce")
    with pytest.raises(duckdb.Error):
        con.cursor().execute("SELECT * FROM read_csv_auto('pyproject.toml')")


def test_chart_validates_llm_choice():
    cols, rows = ["category", "revenue"], [["A", 10.0], ["B", 20.0]]
    good = build_chart({"chart_type": "pie", "x": "category", "y": "revenue", "title": "t"}, cols, rows, "q")
    assert good["type"] == "pie" and good["values"] == [10.0, 20.0]
    # hallucinated column -> heuristic fallback
    bad = build_chart({"chart_type": "bar", "x": "nope", "y": "revenue", "title": ""}, cols, rows, "q")
    assert bad["type"] == "bar" and bad["x"] == "category"


def test_chart_ignores_id_columns():
    cols, rows = ["product_id", "product_name", "unit_price"], [[1, "A", 59.0], [2, "B", 199.0]]
    chart = build_chart({"chart_type": "bar", "x": "product_name", "y": "product_id"}, cols, rows, "q")
    assert chart["y"] == "unit_price"


def test_chart_detects_time_series():
    cols, rows = ["month", "orders"], [["2025-01-01", 5], ["2025-02-01", 7]]
    assert build_chart({"chart_type": "auto"}, cols, rows, "q")["type"] == "line"
