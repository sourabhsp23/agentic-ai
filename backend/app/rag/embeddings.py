"""Text embeddings: Amazon Titan Text Embeddings V2 on Bedrock, or an offline hashing fallback."""

import hashlib
import json
import math
import re
from typing import Protocol

from app.config import Settings


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class BedrockEmbedder:
    def __init__(self, model_id: str, region: str, dim: int) -> None:
        import boto3
        from botocore.config import Config

        self.model_id = model_id
        self.dim = dim
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 2}),
        )

    def embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text[:8000], "dimensions": self.dim, "normalize": True})
        resp = self._client.invoke_model(modelId=self.model_id, body=body)
        return json.loads(resp["body"].read())["embedding"]


class HashingEmbedder:
    """Bag-of-words feature hashing. Not semantic, but good enough for offline tests."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def build_embedder(s: Settings) -> Embedder:
    if s.embedding_provider == "bedrock":
        return BedrockEmbedder(s.embedding_model_id, s.aws_region, s.embedding_dim)
    return HashingEmbedder(s.embedding_dim)
