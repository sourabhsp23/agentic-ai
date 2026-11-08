import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    # inputs
    run_id: str
    dataset: str
    question: str
    # gathered context
    schema: str
    context: list[dict[str, Any]]
    # planner
    plan: dict[str, Any]
    # sql agent
    sql: str
    sql_attempts: int
    sql_error: str | None
    result: dict[str, Any] | None
    # analyst / visualizer / critic
    analysis: dict[str, Any]
    chart: dict[str, Any] | None
    review: dict[str, Any]
    revisions: int
    feedback: str | None
    # output
    final_answer: str
    status: str
    error: str | None
    # append-only logs (merged across parallel branches)
    trace: Annotated[list[dict[str, Any]], operator.add]
    usage: Annotated[list[dict[str, Any]], operator.add]
