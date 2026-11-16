"""Project domain logic.

Projects track milestones, notes, and linked tasks.  Deleting a project
cascades to its milestones and notes via foreign keys; linked tasks are
left in place (their ``project_id`` is set to NULL) so task history is not
lost.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..database import execute, query_one, query_all
from ..models import (
    Milestone,
    MilestoneCreate,
    Note,
    NoteCreate,
    Project,
    ProjectCreate,
    ProjectUpdate,
)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def _row_to_project(row) -> Project:
    return Project(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_project(conn, project_in: ProjectCreate) -> Project:
    now = _now_iso()
    cur = execute(
        conn,
        """
        INSERT INTO projects (title, description, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_in.title, project_in.description, project_in.status, now, now),
    )
    row = query_one(conn, "SELECT * FROM projects WHERE id = ?", (cur.lastrowid,))
    return _row_to_project(row)


def get_project(conn, project_id: int) -> Optional[Project]:
    row = query_one(conn, "SELECT * FROM projects WHERE id = ?", (project_id,))
    return _row_to_project(row) if row else None


def list_projects(conn, status: Optional[str] = None) -> list[Project]:
    sql = "SELECT * FROM projects WHERE 1=1"
    params = []
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC"
    rows = query_all(conn, sql, tuple(params))
    return [_row_to_project(r) for r in rows]


def update_project(
    conn, project_id: int, updates: ProjectUpdate
) -> Optional[Project]:
    row = query_one(conn, "SELECT * FROM projects WHERE id = ?", (project_id,))
    if row is None:
        return None
    data = updates.model_dump(exclude_unset=True)
    if not data:
        return _row_to_project(row)
    data["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [project_id]
    execute(conn, f"UPDATE projects SET {set_clause} WHERE id = ?", tuple(values))
    row = query_one(conn, "SELECT * FROM projects WHERE id = ?", (project_id,))
    return _row_to_project(row) if row else None


def delete_project(conn, project_id: int) -> bool:
    """Delete a project.  Milestones/notes cascade; tasks keep their history."""
    cur = execute(conn, "DELETE FROM projects WHERE id = ?", (project_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

def _row_to_milestone(row) -> Milestone:
    return Milestone(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        due_date=row["due_date"],
        status=row["status"],
        created_at=row["created_at"],
    )


def create_milestone(conn, milestone_in: MilestoneCreate) -> Milestone:
    now = _now_iso()
    cur = execute(
        conn,
        """
        INSERT INTO project_milestones (project_id, title, due_date, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (milestone_in.project_id, milestone_in.title, milestone_in.due_date,
         milestone_in.status, now),
    )
    row = query_one(
        conn, "SELECT * FROM project_milestones WHERE id = ?", (cur.lastrowid,)
    )
    return _row_to_milestone(row)


def list_milestones(conn, project_id: int) -> list[Milestone]:
    rows = query_all(
        conn,
        "SELECT * FROM project_milestones WHERE project_id = ? "
        "ORDER BY due_date IS NULL, due_date, created_at",
        (project_id,),
    )
    return [_row_to_milestone(r) for r in rows]


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def _row_to_note(row) -> Note:
    return Note(
        id=row["id"],
        project_id=row["project_id"],
        content=row["content"],
        created_at=row["created_at"],
    )


def create_note(conn, note_in: NoteCreate) -> Note:
    now = _now_iso()
    cur = execute(
        conn,
        """
        INSERT INTO project_notes (project_id, content, created_at)
        VALUES (?, ?, ?)
        """,
        (note_in.project_id, note_in.content, now),
    )
    row = query_one(conn, "SELECT * FROM project_notes WHERE id = ?", (cur.lastrowid,))
    return _row_to_note(row)


def list_notes(conn, project_id: int) -> list[Note]:
    rows = query_all(
        conn,
        "SELECT * FROM project_notes WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )
    return [_row_to_note(r) for r in rows]


__all__ = [
    "create_project",
    "get_project",
    "list_projects",
    "update_project",
    "delete_project",
    "create_milestone",
    "list_milestones",
    "create_note",
    "list_notes",
]
