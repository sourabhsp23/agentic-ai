"""Dependency container: builds singletons once at startup (DB, LLM, engine, vector store, graph)."""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.agents.graph import AgentDeps, build_graph
from app.config import Settings
from app.db.session import build_engine, init_db
from app.llm.factory import get_llm
from app.rag.embeddings import build_embedder
from app.rag.store import InMemoryVectorStore, PgVectorStore, ingest_directory
from app.tools.sql_engine import SQLEngine
from app.tools.storage import LocalStorage, S3Storage, build_storage

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    db_engine: Engine
    sessions: sessionmaker
    storage: LocalStorage | S3Storage
    sql_engine: SQLEngine
    store: InMemoryVectorStore | PgVectorStore
    graph: object

    def reindex_knowledge(self) -> int:
        return ingest_directory(self.store, Path(self.settings.knowledge_dir))


def build_container(settings: Settings) -> Container:
    db_engine = build_engine(settings.database_url)
    sessions = init_db(db_engine)
    storage = build_storage(settings)
    sql_engine = SQLEngine(storage, max_rows=settings.max_result_rows)
    embedder = build_embedder(settings)
    if db_engine.dialect.name == "postgresql":
        store: InMemoryVectorStore | PgVectorStore = PgVectorStore(db_engine, embedder)
    else:
        store = InMemoryVectorStore(embedder)
    graph = build_graph(AgentDeps(llm=get_llm(), engine=sql_engine, store=store, settings=settings))
    container = Container(settings, db_engine, sessions, storage, sql_engine, store, graph)
    if store.count() == 0:
        container.reindex_knowledge()
    log.info(
        "Container ready (llm=%s, db=%s, storage=%s)",
        settings.llm_provider,
        db_engine.dialect.name,
        settings.storage_backend,
    )
    return container
