from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base


def build_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # share one in-memory DB across threads
    return create_engine(url, **kwargs)


def init_db(engine: Engine) -> sessionmaker:
    # For a real migration workflow, see docs/ROADMAP.md (Alembic is a planned lesson).
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
