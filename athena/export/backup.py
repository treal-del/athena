"""Export and backup for Athena.

User data lives in a local SQLite database.  This module provides:

* :func:`backup_database` — a timestamped copy of the SQLite file.
* :func:`export_json` — all tables dumped to a single JSON file.
* :func:`export_archive` — a zip archive containing the database and JSON export.

No secrets are ever included (there are none in the database).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import BACKUP_DIR, DB_PATH
from ..database import connect


def _now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


TABLES = [
    "meta",
    "tasks",
    "fixed_commitments",
    "memories",
    "projects",
    "project_milestones",
    "project_notes",
]


def backup_database(dest: Optional[Path] = None, db_path: Path = DB_PATH) -> Path:
    """Copy the live SQLite database to ``dest`` or a timestamped backup file.

    Returns the path to the backup.  ``db_path`` defaults to the configured
    database but can be overridden (e.g. in tests).
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if dest is None:
        dest = BACKUP_DIR / f"athena_backup_{_now_stamp()}.db"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(db_path), str(dest))
    return dest


def export_json(dest: Path, db_path: Path = DB_PATH) -> Path:
    """Dump every table to a JSON file keyed by table name."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        data: dict[str, list[dict]] = {}
        for table in TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(r) for r in rows]
    finally:
        conn.close()
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return dest


def export_archive(dest: Optional[Path] = None, db_path: Path = DB_PATH) -> Path:
    """Create a zip archive containing the database and a JSON export."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if dest is None:
        dest = BACKUP_DIR / f"athena_export_{_now_stamp()}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    json_path = BACKUP_DIR / f"athena_export_{_now_stamp()}.json"
    try:
        export_json(json_path, db_path=db_path)
        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(db_path), arcname="athena.db")
            zf.write(str(json_path), arcname="athena_export.json")
    finally:
        if json_path.exists():
            json_path.unlink()
    return dest


__all__ = ["backup_database", "export_json", "export_archive"]
