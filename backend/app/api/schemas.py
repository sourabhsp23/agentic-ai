from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    dataset: str = Field(..., pattern=r"^[A-Za-z0-9_-]{1,64}$", examples=["ecommerce"])
    question: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        examples=["What are the top 5 product categories by revenue?"],
    )


class TableSchema(BaseModel):
    name: str
    row_count: int
    columns: list[tuple[str, str]]


class DatasetOut(BaseModel):
    name: str
    files: list[str]


class RunOut(BaseModel):
    id: str
    created_at: str
    dataset: str
    question: str
    status: str
    answer: str | None
    sql: str | None
    chart: dict | None
    trace: list | None
    model: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
