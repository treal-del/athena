"""Tests for the database layer: schema, versioning, migrations."""

from __future__ import annotations

import pytest

from athena.database import connect, get_db_version, init_db, migrate, set_db_version


def test_schema_version_stored(db_path):
    with connect(db_path) as c:
        assert get_db_version(c) == 2


def test_required_tables_exist(conn):
    expected = {
        "meta",
        "tasks",
        "fixed_commitments",
        "memories",
        "projects",
        "project_milestones",
        "project_notes",
    }
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert expected.issubset(names)


def test_foreign_keys_enforced(conn):
    conn.execute("BEGIN")
    try:
        with pytest.raises(Exception):
            conn.execute(
                "INSERT INTO tasks (title, status, created_at, updated_at, project_id) "
                "VALUES ('x', 'todo', '2024-01-01', '2024-01-01', 99999)"
            )
        conn.execute("ROLLBACK")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def test_init_db_is_idempotent(db_path):
    init_db(db_path)
    init_db(db_path)
    with connect(db_path) as c:
        assert get_db_version(c) == 2


def test_set_and_get_db_version(conn):
    set_db_version(conn, 5)
    assert get_db_version(conn) == 5


def test_migrate_unknown_version_raises(conn):
    with pytest.raises(RuntimeError, match="version 3"):
        migrate(conn, 2, 3)
