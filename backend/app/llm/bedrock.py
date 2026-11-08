"""Amazon Bedrock client using the unified Converse API + forced tool use.

Works with any Converse-compatible model that supports tool use
(Amazon Nova, Anthropic Claude, Mistral Large, Llama 3.1+ ...).

Credentials come from the standard AWS chain: env vars, ~/.aws/credentials,
EC2 instance profile, ECS task role, or EKS IRSA / Pod Identity. Never hard-code keys.
"""

import json
import logging
import re
import time
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.llm.base import LLMError, LLMResult
from app.observability.metrics import LLM_CALLS, LLM_TOKENS

log = logging.getLogger(__name__)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class BedrockLLM:
    def __init__(
        self,
        model_id: str,
        region: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: int = 60,
    ) -> None:
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                read_timeout=timeout,
                retries={"max_attempts": 5, "mode": "adaptive"},  # handles throttling
            ),
        )

    def structured(
        self,
        *,
        system: str,
        prompt: str,
        tool_name: str,
        tool_description: str,
        schema: dict[str, Any],
    ) -> LLMResult:
        request = {
            "modelId": self.model_id,
            "system": [{"text": system}],
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": self.temperature, "maxTokens": self.max_tokens},
            "toolConfig": {
                "tools": [
                    {
                        "toolSpec": {
                            "name": tool_name,
                            "description": tool_description,
                            "inputSchema": {"json": schema},
                        }
                    }
                ],
                # "any" with a single tool == force the model to call it.
                "toolChoice": {"any": {}},
            },
        }
        start = time.perf_counter()
        try:
            response = self._client.converse(**request)
        except (ClientError, BotoCoreError) as exc:
            LLM_CALLS.labels(self.model_id, "error").inc()
            log.exception("Bedrock converse failed")
            raise LLMError(f"Bedrock call failed: {exc}") from exc
        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.get("usage", {})
        in_tok, out_tok = usage.get("inputTokens", 0), usage.get("outputTokens", 0)
        LLM_CALLS.labels(self.model_id, "ok").inc()
        LLM_TOKENS.labels(self.model_id, "input").inc(in_tok)
        LLM_TOKENS.labels(self.model_id, "output").inc(out_tok)

        content = response["output"]["message"]["content"]
        text = "".join(block.get("text", "") for block in content)
        data = next(
            (b["toolUse"]["input"] for b in content if "toolUse" in b and b["toolUse"]["name"] == tool_name),
            None,
        )
        if data is None:  # Fallback: some models answer with JSON in plain text.
            match = _JSON_RE.search(text)
            if not match:
                raise LLMError(f"Model did not call tool '{tool_name}'. Output: {text[:300]}")
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise LLMError(f"Could not parse model JSON: {exc}") from exc

        return LLMResult(
            data=data,
            model=self.model_id,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            raw_text=text,
        )
