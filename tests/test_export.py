"""Tests for export and backup."""

from __future__ import annotations

import json
import zipfile

from athena.export import backup_database, export_json, export_archive
from athena.config import BACKUP_DIR


def test_backup_database_creates_file(tmp_path, db_path):
    out = backup_database(tmp_path / "my_backup.db", db_path=db_path)
    assert out.exists()
    assert out.suffix == ".db"
    # It should be a valid SQLite copy.
    import sqlite3
    conn = sqlite3.connect(str(out))
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert len(tables) > 0
    finally:
        conn.close()


def test_export_json(tmp_path, db_path):
    out = export_json(tmp_path / "data.json", db_path=db_path)
    assert out.exists()
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert "tasks" in data and "memories" in data and "projects" in data


def test_export_archive(tmp_path, db_path):
    out = export_archive(tmp_path / "archive.zip", db_path=db_path)
    assert out.exists()
    assert zipfile.is_zipfile(str(out))
    with zipfile.ZipFile(str(out)) as zf:
        names = set(zf.namelist())
        assert "athena.db" in names
        assert "athena_export.json" in names
