"""Task domain logic.

All functions expect an open :class:`sqlite3.Connection` as the first
argument.  The caller is responsible for opening the connection and, when
multiple operations must be atomic, wrapping them in
:func:`athena.database.transaction`.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional

from ..database import execute, query_one, query_all
from ..models import Task, TaskCreate, TaskUpdate

VALID_PRIORITIES = ("low", "medium", "high", "critical")
VALID_STATUSES = ("todo", "in_progress", "done", "cancelled")


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _row_to_task(row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        priority=row["priority"],
        estimated_minutes=row["estimated_minutes"] or 0,
        due_date=row["due_date"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        project_id=row["project_id"],
    )


def create_task(conn, task_in: TaskCreate) -> Task:
    """Insert a new task and return the persisted :class:`Task`."""
    now = _now_iso()
    cur = execute(
        conn,
        """
        INSERT INTO tasks
            (title, description, priority, estimated_minutes, due_date, status,
             created_at, updated_at, completed_at, project_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_in.title,
            task_in.description,
            task_in.priority,
            task_in.estimated_minutes,
            task_in.due_date,
            task_in.status,
            now,
            now,
            None if task_in.status != "done" else now,
            task_in.project_id,
        ),
    )
    task_id = cur.lastrowid
    row = query_one(conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))
    return _row_to_task(row)


def get_task(conn, task_id: int) -> Optional[Task]:
    """Return a task by id, or ``None`` if it does not exist."""
    row = query_one(conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))
    return _row_to_task(row) if row else None


def list_tasks(
    conn,
    *,
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    overdue_only: bool = False,
    due_before: Optional[str] = None,
) -> list[Task]:
    """List tasks with optional filters.

    Parameters are combined with AND.  When ``overdue_only`` is set, only
    incomplete tasks with a due date earlier than today are returned.
    """
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    if project_id is not None:
        sql += " AND project_id = ?"
        params.append(project_id)
    if due_before is not None:
        sql += " AND due_date IS NOT NULL AND due_date < ?"
        params.append(due_before)
    if overdue_only:
        today = date.today().isoformat()
        sql += " AND status != 'done' AND due_date IS NOT NULL AND due_date < ?"
        params.append(today)
    sql += " ORDER BY due_date IS NULL, due_date, priority, created_at"
    rows = query_all(conn, sql, tuple(params))
    return [_row_to_task(r) for r in rows]


def update_task(conn, task_id: int, updates: TaskUpdate) -> Optional[Task]:
    """Update fields on a task.

    Returns the updated task, or ``None`` if no task with that id exists.
    When status transitions to ``done`` the ``completed_at`` timestamp is set;
    when it leaves ``done`` the timestamp is cleared.
    """
    row = query_one(conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))
    if row is None:
        return None

    current = _row_to_task(row)
    data = updates.model_dump(exclude_unset=True)
    if not data:
        return current

    now = _now_iso()
    data["updated_at"] = now

    new_status = data.get("status", current.status)
    if new_status == "done" and current.status != "done":
        data["completed_at"] = now
    elif new_status != "done":
        data["completed_at"] = None

    set_clause = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [task_id]
    execute(conn, f"UPDATE tasks SET {set_clause} WHERE id = ?", tuple(values))

    row = query_one(conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))
    return _row_to_task(row)


def delete_task(conn, task_id: int) -> bool:
    """Delete a task.  Returns True if a row was removed."""
    cur = execute(conn, "DELETE FROM tasks WHERE id = ?", (task_id,))
    return cur.rowcount > 0


def get_overdue_tasks(conn) -> list[Task]:
    """Return incomplete tasks whose due date is earlier than today."""
    today = date.today().isoformat()
    rows = query_all(
        conn,
        "SELECT * FROM tasks WHERE status != 'done' AND due_date IS NOT NULL "
        "AND due_date < ? ORDER BY due_date",
        (today,),
    )
    return [_row_to_task(r) for r in rows]


def get_due_soon(conn, days: int = 3) -> list[Task]:
    """Return incomplete tasks due within the next ``days`` days (inclusive)."""
    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=days)).isoformat()
    rows = query_all(
        conn,
        "SELECT * FROM tasks WHERE status != 'done' AND due_date IS NOT NULL "
        "AND due_date >= ? AND due_date <= ? ORDER BY due_date",
        (today, horizon),
    )
    return [_row_to_task(r) for r in rows]


def get_today_tasks(conn) -> list[Task]:
    """Return tasks due today (any status)."""
    today = date.today().isoformat()
    rows = query_all(
        conn,
        "SELECT * FROM tasks WHERE due_date = ? ORDER BY created_at",
        (today,),
    )
    return [_row_to_task(r) for r in rows]


__all__ = [
    "create_task",
    "get_task",
    "list_tasks",
    "update_task",
    "delete_task",
    "get_overdue_tasks",
    "get_due_soon",
    "get_today_tasks",
    "VALID_PRIORITIES",
    "VALID_STATUSES",
]

