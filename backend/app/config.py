"""Centralised, environment-driven configuration (12-factor style).

Every setting can be overridden with an environment variable of the same
name (case-insensitive), or via a `.env` file in the working directory.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App -------------------------------------------------------------
    app_name: str = "InsightPilot"
    app_env: Literal["local", "dev", "staging", "prod", "test"] = "local"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    # Optional shared-secret auth. When set, every /api call needs `X-API-Key`.
    api_key: str | None = None

    # --- LLM (Amazon Bedrock) -------------------------------------------
    # "bedrock" for real calls, "fake" for offline dev / CI (no AWS needed).
    llm_provider: Literal["bedrock", "fake"] = "fake"
    aws_region: str = "us-east-1"
    # Optional Bedrock API key (local dev). Leave unset on AWS, where IAM roles are used.
    aws_bearer_token_bedrock: str | None = Field(default=None, repr=False)
    # Cross-region inference profile. Swap for e.g. us.amazon.nova-pro-v1:0
    # or us.anthropic.claude-3-5-haiku-20241022-v1:0
    bedrock_model_id: str = "us.amazon.nova-lite-v1:0"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048
    llm_timeout_seconds: int = 60

    # --- Embeddings / RAG ------------------------------------------------
    embedding_provider: Literal["bedrock", "fake"] = "fake"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_dim: int = 1024
    rag_top_k: int = 4
    knowledge_dir: Path = Path("../knowledge")

    # --- Persistence -----------------------------------------------------
    # sqlite for local dev; postgresql+psycopg://... in docker / AWS (RDS).
    database_url: str = "sqlite:///./insightpilot.db"

    # --- Dataset storage -------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    data_dir: Path = Path("../sample_data")
    s3_bucket: str | None = None
    s3_prefix: str = "datasets/"
    cache_dir: Path = Path("./.cache/datasets")

    # --- Agent behaviour -------------------------------------------------
    max_sql_attempts: int = 3
    max_revisions: int = 1
    max_result_rows: int = 200


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # boto3 reads the Bedrock API key only from the process environment, while
    # pydantic-settings does not export .env values, so bridge it here.
    if settings.aws_bearer_token_bedrock:
        os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", settings.aws_bearer_token_bedrock)
    return settings
