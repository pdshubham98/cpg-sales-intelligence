"""
Shared pytest fixtures. Each test gets its own temp SQLite file (tmp_path).
Connections are always closed before yielding so subsequent opens don't block.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key")


def _seed_db(db_file: Path) -> None:
    """Create schema and insert reference + transaction rows."""
    env = {"DB_PATH": str(db_file)}
    with patch.dict(os.environ, env):
        from src.ingestion.schema import create_schema, get_connection
        create_schema()
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO regions VALUES "
                "('R001','North America','USA','Alice')"
            )
            conn.execute(
                "INSERT OR IGNORE INTO products VALUES "
                "('P001','BEV-001','Sparkling Water','Beverages',1.99)"
            )
            for i in range(1, 16):
                month = (
                    f"2024-{i:02d}-15" if i <= 12 else f"2025-{(i - 12):02d}-15"
                )
                conn.execute(
                    "INSERT OR IGNORE INTO sales_transactions VALUES "
                    "(?,?,?,?,?,?,?,?,?,?)",
                    (
                        f"T{i:04d}", month, "R001", "P001", "BEV-001",
                        100 + i * 5, 1.99, 0.05, "Retail",
                        round((100 + i * 5) * 1.99 * 0.95, 2),
                    ),
                )
            conn.commit()


@pytest.fixture(scope="function")
def populated_db(tmp_path):
    """Temp DB seeded with 15 monthly transactions. Yields db_file path."""
    db_file = tmp_path / "test.db"
    _seed_db(db_file)
    yield db_file


@pytest.fixture(scope="function")
def api_client(tmp_path):
    """FastAPI TestClient against a seeded DB; lifespan ingestion is mocked."""
    db_file = tmp_path / "test.db"
    _seed_db(db_file)

    env = {
        "DB_PATH": str(db_file),
        "LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "test-key",
    }
    with patch.dict(os.environ, env):
        with patch("src.ingestion.loader.run_ingestion"):
            from src.api.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                yield client
