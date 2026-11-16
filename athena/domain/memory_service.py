"""Memory domain logic.

Memories are approved-by-default-false items the user wants Athena to
remember: profile facts, goals, events, and knowledge notes.  Each memory
carries a ``source`` so the user can tell where a piece of information came
from, and an ``approved`` flag that gates whether it is used in reports and
retrieval.

Security note: memories are conversational, personal data.  Never store
passwords, authentication tokens, or private keys in a memory.  This module
does not scan for secrets; that responsibility is documented and enforced at
the UI/ingestion boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from ..database import execute, query_one, query_all
from ..models import Memory, MemoryCreate, MemoryUpdate

VALID_KINDS = ("profile_fact", "goal", "event", "knowledge_note")


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _row_to_memory(row) -> Memory:
    return Memory(
        id=row["id"],
        kind=row["kind"],
        content=row["content"],
        source=row["source"],
        approved=bool(row["approved"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_memory(conn, memory_in: MemoryCreate) -> Memory:
    """Insert a new memory (unapproved by default) and return it."""
    now = _now_iso()
    cur = execute(
        conn,
        """
        INSERT INTO memories (kind, content, source, approved, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            memory_in.kind,
            memory_in.content,
            memory_in.source,
            1 if memory_in.approved else 0,
            now,
            now,
        ),
    )
    row = query_one(conn, "SELECT * FROM memories WHERE id = ?", (cur.lastrowid,))
    return _row_to_memory(row)


def get_memory(conn, memory_id: int) -> Optional[Memory]:
    """Return a memory by id, or ``None`` if it does not exist."""
    row = query_one(conn, "SELECT * FROM memories WHERE id = ?", (memory_id,))
    return _row_to_memory(row) if row else None


def list_memories(
    conn,
    *,
    kind: Optional[str] = None,
    approved: Optional[bool] = None,
) -> list[Memory]:
    """List memories, optionally filtered by kind and approval status."""
    sql = "SELECT * FROM memories WHERE 1=1"
    params: list = []
    if kind is not None:
        sql += " AND kind = ?"
        params.append(kind)
    if approved is not None:
        sql += " AND approved = ?"
        params.append(1 if approved else 0)
    sql += " ORDER BY created_at DESC"
    rows = query_all(conn, sql, tuple(params))
    return [_row_to_memory(r) for r in rows]


def search_memories(
    conn,
    query: str,
    *,
    kind: Optional[str] = None,
    approved_only: bool = False,
    limit: int = 50,
) -> list[Memory]:
    """Search memories by keyword.

    A simple case-insensitive LIKE over ``content`` and ``source``.  Results
    are returned with their timestamps and source so the user can evaluate
    where each memory came from.
    """
    like = f"%{query}%"
    sql = (
        "SELECT * FROM memories WHERE (content LIKE ? OR source LIKE ?)"
    )
    params: list = [like, like]
    if kind is not None:
        sql += " AND kind = ?"
        params.append(kind)
    if approved_only:
        sql += " AND approved = 1"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = query_all(conn, sql, tuple(params))
    return [_row_to_memory(r) for r in rows]


def update_memory(
    conn, memory_id: int, updates: MemoryUpdate
) -> Optional[Memory]:
    """Update fields on a memory.  Returns the updated memory or ``None``."""
    row = query_one(conn, "SELECT * FROM memories WHERE id = ?", (memory_id,))
    if row is None:
        return None

    data = updates.model_dump(exclude_unset=True)
    if not data:
        return _row_to_memory(row)

    now = _now_iso()
    data["updated_at"] = now
    if "approved" in data and isinstance(data["approved"], bool):
        data["approved"] = 1 if data["approved"] else 0

    set_clause = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [memory_id]
    execute(conn, f"UPDATE memories SET {set_clause} WHERE id = ?", tuple(values))

    row = query_one(conn, "SELECT * FROM memories WHERE id = ?", (memory_id,))
    return _row_to_memory(row)


def approve_memory(conn, memory_id: int, approved: bool = True) -> Optional[Memory]:
    """Set the approval flag on a memory and return it, or ``None``."""
    now = _now_iso()
    cur = execute(
        conn,
        "UPDATE memories SET approved = ?, updated_at = ? WHERE id = ?",
        (1 if approved else 0, now, memory_id),
    )
    if cur.rowcount == 0:
        return None
    row = query_one(conn, "SELECT * FROM memories WHERE id = ?", (memory_id,))
    return _row_to_memory(row) if row else None


def delete_memory(conn, memory_id: int) -> bool:
    """Delete a memory.  Returns True if a row was removed."""
    cur = execute(conn, "DELETE FROM memories WHERE id = ?", (memory_id,))
    return cur.rowcount > 0


__all__ = [
    "create_memory",
    "get_memory",
    "list_memories",
    "search_memories",
    "update_memory",
    "approve_memory",
    "delete_memory",
    "VALID_KINDS",
]

