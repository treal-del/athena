"""Configuration for Athena.

All configuration is read from environment variables (loaded from a ``.env``
file when present) with sensible defaults. No secrets are stored in source
files or in the database.

Database versioning strategy:
    The schema version is stored in the SQLite ``meta`` table under the key
    ``db_version``.  When a breaking schema change is needed, the version is
    bumped and a migration function is added to :func:`athena.database.migrate`
    that transforms the database from version N to N+1.  Migration functions
    run inside a single transaction so a failure never leaves a half-migrated
    database.
"""

from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv is optional but recommended for local development
    from dotenv import load_dotenv

    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except Exception:  # pragma: no cover - dotenv is a convenience, not a requirement
    pass


def env(name: str, default: str = "") -> str:
    """Read an environment variable, returning ``default`` when unset."""
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

# Directory that holds the SQLite database and any exports/backups.
# Defaults to a ``data`` folder next to the project root.
DATA_DIR = Path(env("ATHENA_DATA_DIR", "data")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / env("ATHENA_DB_NAME", "athena.db")
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

DB_VERSION = 2

# ---------------------------------------------------------------------------
# AI provider configuration (optional)
# ---------------------------------------------------------------------------

AI_PROVIDER = env("ATHENA_AI_PROVIDER").strip()
AI_API_KEY = env("ATHENA_AI_API_KEY").strip()


__all__ = [
    "DATA_DIR",
    "DB_PATH",
    "BACKUP_DIR",
    "DB_VERSION",
    "AI_PROVIDER",
    "AI_API_KEY",
    "env",
]
