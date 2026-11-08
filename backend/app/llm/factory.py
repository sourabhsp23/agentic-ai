from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMClient


@lru_cache
def get_llm() -> LLMClient:
    s = get_settings()
    if s.llm_provider == "bedrock":
        from app.llm.bedrock import BedrockLLM

        return BedrockLLM(
            model_id=s.bedrock_model_id,
            region=s.aws_region,
            temperature=s.llm_temperature,
            max_tokens=s.llm_max_tokens,
            timeout=s.llm_timeout_seconds,
        )
    from app.llm.fake import FakeLLM

    return FakeLLM()
