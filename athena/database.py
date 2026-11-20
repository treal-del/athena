"""SQLite data access layer for Athena.

All database queries and schema logic live here.  The Streamlit UI and domain
services never execute raw SQL directly; they go through the functions and
connection helpers defined in this module.

Design notes
------------
* One connection per operation (opened via :func:`connect`), used inside a
  context manager so it commits on success and rolls back on failure.
* Schema version is tracked in the ``meta`` table (see ``config.DB_VERSION``).
* Migrations run inside a transaction; a migration failure raises and leaves
  the database untouched, so information is never silently lost.
* Foreign keys are enforced on every connection.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .config import BACKUP_DIR, DB_PATH, DB_VERSION

__all__ = [
    "connect",
    "init_db",
    "migrate",
    "get_db_version",
    "set_db_version",
    "execute",
    "query_one",
    "query_all",
]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults.

    * ``foreign_keys=ON`` — enforce referential integrity.
    * ``row_factory=sqlite3.Row`` — rows behave like dicts.
    * ``timeout=30`` — wait briefly if the DB is locked by another process.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Yield a connection inside an explicit transaction.

    Commits on success; rolls back on any exception.  This is the mechanism
    that guarantees migrations and multi-statement writes are atomic.
    """
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT NOT NULL,
    description    TEXT,
    priority       TEXT NOT NULL DEFAULT 'medium',
    estimated_minutes INTEGER NOT NULL DEFAULT 0,
    due_date       TEXT,
    status         TEXT NOT NULL DEFAULT 'todo',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    completed_at   TEXT,
    project_id     INTEGER REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS fixed_commitments (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title    TEXT NOT NULL,
    start_dt TEXT NOT NULL,
    end_dt   TEXT NOT NULL,
    source   TEXT
);

CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT,
    approved    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    due_date    TEXT,
    status      TEXT NOT NULL DEFAULT 'upcoming',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status      ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date    ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_project     ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_kind     ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_approved ON memories(approved);
CREATE INDEX IF NOT EXISTS idx_memories_created  ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_status   ON projects(status);

CREATE TABLE IF NOT EXISTS availability_settings (
    id                   INTEGER PRIMARY KEY CHECK (id = 1),
    work_start           TEXT NOT NULL DEFAULT '09:00',
    work_end             TEXT NOT NULL DEFAULT '17:00',
    lunch_start          TEXT,
    lunch_end            TEXT,
    break_every_minutes  INTEGER NOT NULL DEFAULT 120,
    break_duration_minutes INTEGER NOT NULL DEFAULT 15,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_availability_settings_id ON availability_settings(id);
"""


def init_db(db_path: Path = DB_PATH) -> int:
    """Create the schema (if missing) and run migrations.

    Returns the final database version.  Safe to call on every application
    start — creating tables is idempotent and migrations are only applied
    when the stored version is lower than ``config.DB_VERSION``.
    """
    with connect(db_path) as conn:
        # executescript implicitly commits any open transaction, so run the
        # DDL outside the explicit versioning transaction.
        conn.executescript(_SCHEMA_V1)
        with transaction(conn):
            current = get_db_version(conn)
            if current < DB_VERSION:
                migrate(conn, current, DB_VERSION)
            set_db_version(conn, DB_VERSION)
    return DB_VERSION


def get_db_version(conn: sqlite3.Connection) -> int:
    """Return the stored schema version (0 if never initialized)."""
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'db_version'"
    ).fetchone()
    return int(row["value"]) if row else 0


def set_db_version(conn: sqlite3.Connection, version: int) -> None:
    """Persist the schema version."""
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('db_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

# Migration functions take a connection and the *from* version, and advance
# the schema by exactly one version.  They are registered by target version.

def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Placeholder: v1 is the initial schema, nothing to migrate."""
    return


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Add availability_settings table for configurable planner availability."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS availability_settings (
            id                   INTEGER PRIMARY KEY CHECK (id = 1),
            work_start           TEXT NOT NULL DEFAULT '09:00',
            work_end             TEXT NOT NULL DEFAULT '17:00',
            lunch_start          TEXT,
            lunch_end            TEXT,
            break_every_minutes  INTEGER NOT NULL DEFAULT 120,
            break_duration_minutes INTEGER NOT NULL DEFAULT 15,
            updated_at           TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO availability_settings
            (id, work_start, work_end, lunch_start, lunch_end,
             break_every_minutes, break_duration_minutes, updated_at)
        VALUES (1, '09:00', '17:00', '12:00', '13:00', 120, 15, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (datetime.utcnow().isoformat(),),
    )


_MIGRATIONS = {
    1: _migrate_v1,
    2: _migrate_v2,
}


def migrate(conn: sqlite3.Connection, from_version: int, to_version: int) -> None:
    """Run migrations from ``from_version`` up to ``to_version`` (exclusive).

    Each step runs inside the same transaction opened by the caller, so a
    failure rolls the entire migration back.
    """
    for version in range(from_version + 1, to_version + 1):
        step = _MIGRATIONS.get(version)
        if step is None:
            raise RuntimeError(
                f"No migration registered to reach schema version {version}"
            )
        step(conn)
        set_db_version(conn, version)


# ---------------------------------------------------------------------------
# Low-level query helpers
# ---------------------------------------------------------------------------

def execute(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute a single statement and return the cursor."""
    return conn.execute(sql, params)


def query_one(
    conn: sqlite3.Connection, sql: str, params: tuple = ()
) -> Optional[sqlite3.Row]:
    """Execute a query and return the first row, or ``None``."""
    return conn.execute(sql, params).fetchone()


def query_all(
    conn: sqlite3.Connection, sql: str, params: tuple = ()
) -> list[sqlite3.Row]:
    """Execute a query and return all rows."""
    return conn.execute(sql, params).fetchall()


