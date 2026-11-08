import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Configure the app for offline, hermetic tests BEFORE importing it.
os.environ.update(
    {
        "APP_ENV": "test",
        "LLM_PROVIDER": "fake",
        "EMBEDDING_PROVIDER": "fake",
        "STORAGE_BACKEND": "local",
        "DATA_DIR": str(ROOT / "sample_data"),
        "KNOWLEDGE_DIR": str(ROOT / "knowledge"),
        "DATABASE_URL": "sqlite://",  # in-memory
    }
)
os.environ.pop("API_KEY", None)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
