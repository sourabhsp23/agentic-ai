"""Vector store for business knowledge (metric definitions, glossary, rules).

- PostgreSQL + pgvector when DATABASE_URL is Postgres (docker-compose / Amazon RDS)
- In-memory cosine similarity otherwise (sqlite / tests)
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, text

from app.rag.embeddings import Embedder

log = logging.getLogger(__name__)


@dataclass
class Chunk:
    source: str
    content: str
    score: float = 0.0


def chunk_markdown(source: str, markdown: str) -> list[Chunk]:
    """Split a markdown doc on `##` headings; each section becomes one chunk."""
    sections = re.split(r"\n(?=## )", markdown)
    return [Chunk(source, s.strip()) for s in sections if len(s.strip()) > 20]


class InMemoryVectorStore:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._items: list[tuple[Chunk, list[float]]] = []

    def count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()

    def add(self, chunks: list[Chunk]) -> None:
        self._items += [(c, self.embedder.embed(c.content)) for c in chunks]

    def search(self, query: str, k: int) -> list[Chunk]:
        q = self.embedder.embed(query)
        scored = [
            Chunk(c.source, c.content, sum(a * b for a, b in zip(q, v, strict=False))) for c, v in self._items
        ]
        return sorted(scored, key=lambda c: c.score, reverse=True)[:k]


class PgVectorStore:
    def __init__(self, engine: Engine, embedder: Embedder) -> None:
        self.engine = engine
        self.embedder = embedder
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    f"""CREATE TABLE IF NOT EXISTS knowledge_chunks (
                        id SERIAL PRIMARY KEY,
                        source TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector({embedder.dim}) NOT NULL)"""
                )
            )

    @staticmethod
    def _vec(v: list[float]) -> str:
        return "[" + ",".join(f"{x:.6f}" for x in v) + "]"

    def count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT COUNT(*) FROM knowledge_chunks")).scalar_one()

    def clear(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE knowledge_chunks"))

    def add(self, chunks: list[Chunk]) -> None:
        rows = [
            {"s": c.source, "c": c.content, "e": self._vec(self.embedder.embed(c.content))} for c in chunks
        ]
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO knowledge_chunks (source, content, embedding) "
                    "VALUES (:s, :c, CAST(:e AS vector))"
                ),
                rows,
            )

    def search(self, query: str, k: int) -> list[Chunk]:
        q = self._vec(self.embedder.embed(query))
        sql = text(
            """SELECT source, content, 1 - (embedding <=> CAST(:q AS vector)) AS score
               FROM knowledge_chunks ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"""
        )
        with self.engine.connect() as conn:
            return [Chunk(r.source, r.content, float(r.score)) for r in conn.execute(sql, {"q": q, "k": k})]


def ingest_directory(store: InMemoryVectorStore | PgVectorStore, folder: Path) -> int:
    chunks: list[Chunk] = []
    if folder.is_dir():
        for md in sorted(folder.glob("*.md")):
            chunks += chunk_markdown(md.name, md.read_text(encoding="utf-8"))
    store.clear()
    if chunks:
        store.add(chunks)
    log.info("Indexed %d knowledge chunks from %s", len(chunks), folder)
    return len(chunks)
