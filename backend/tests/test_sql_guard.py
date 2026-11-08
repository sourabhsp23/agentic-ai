import pytest

from app.tools.sql_guard import UnsafeSQLError, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select * from orders limit 5;",
        "WITH t AS (SELECT 1 AS a) SELECT a FROM t",
        "SELECT a FROM x UNION ALL SELECT b FROM y",
        "SELECT date_trunc('month', order_date) m, COUNT(*) FROM orders GROUP BY 1",
    ],
)
def test_allows_read_only(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE orders",
        "DELETE FROM orders",
        "INSERT INTO orders VALUES (1)",
        "UPDATE orders SET status = 'x'",
        "CREATE TABLE x AS SELECT 1",
        "SELECT 1; DROP TABLE orders",
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "COPY orders TO 'out.csv'",
        "ATTACH 'evil.db'",
        "",
    ],
)
def test_blocks_unsafe(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)
