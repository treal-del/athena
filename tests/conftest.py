"""Pytest fixtures for Athena.

Every test gets a fresh SQLite database in a temporary directory so tests
never touch the real user data.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from athena.database import connect, init_db


@pytest.fixture
def db_path() -> Path:
    """A fresh temp database path, schema initialized."""
    tmp = Path(tempfile.mkdtemp(prefix="athena_test_"))
    db = tmp / "athena.db"
    init_db(db)
    return db


@pytest.fixture
def conn(db_path: Path):
    """Open a connection to the temp database."""
    with connect(db_path) as c:
        yield c
