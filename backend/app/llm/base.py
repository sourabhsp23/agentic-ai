"""Provider-agnostic LLM interface.

Agents only ever ask for *structured* output: "call this tool with JSON that
matches this schema". That keeps every agent's output machine-checkable.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMResult:
    data: dict[str, Any]
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    raw_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    model_id: str

    def structured(
        self,
        *,
        system: str,
        prompt: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
    ) -> LLMResult: ...


class LLMError(RuntimeError):
    """Raised when the model fails or returns unusable output."""


# Approximate on-demand prices (USD per 1M tokens: input, output).
# Prices change; treat this as an estimate and verify on the Bedrock pricing page.
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "amazon.nova-micro": (0.035, 0.14),
    "amazon.nova-lite": (0.06, 0.24),
    "amazon.nova-pro": (0.80, 3.20),
    "anthropic.claude-3-5-haiku": (0.80, 4.00),
    "anthropic.claude-3-haiku": (0.25, 1.25),
    "fake": (0.0, 0.0),
}


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    for key, (p_in, p_out) in PRICING_PER_MTOK.items():
        if key in model_id:
            return (input_tokens * p_in + output_tokens * p_out) / 1_000_000
    return 0.0
