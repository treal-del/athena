"""Reporting domain logic.

Reports are generated from actual database records only.  Each report
clearly distinguishes *recorded facts* (data stored in the database) from
*estimates* (values derived without measurement, such as estimated task
durations).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from ..database import query_all, query_one
from ..models import Task

DAY_AGGREGATE = "daily"
WEEK_AGGREGATE = "weekly"


def _iso(d: date) -> str:
    return d.isoformat()


def _start_of_week(d: date) -> date:
    """Monday of the week containing ``d``."""
    return d - timedelta(days=d.weekday())


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _task_summary(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "priority": row["priority"],
        "due_date": row["due_date"],
        "estimated_minutes": row["estimated_minutes"] or 0,
        "project_id": row["project_id"],
        "completed_at": row["completed_at"],
    }


def _memory_summary(row) -> dict:
    return {
        "id": row["id"],
        "kind": row["kind"],
        "content": row["content"],
        "source": row["source"],
        "approved": bool(row["approved"]),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Daily report
# ---------------------------------------------------------------------------

def daily_report(conn, day: Optional[date] = None) -> dict:
    """Return a report for a single day (defaults to today).

    Recorded facts come from the database.  Estimates (e.g. estimated
    minutes) are explicitly labeled.
    """
    target = day or date.today()
    iso = _iso(target)

    tasks_due = query_all(
        conn,
        "SELECT * FROM tasks WHERE due_date = ? ORDER BY priority, created_at",
        (iso,),
    )
    tasks_completed = query_all(
        conn,
        "SELECT * FROM tasks WHERE status = 'done' AND completed_at IS NOT NULL "
        "AND date(completed_at) = ? ORDER BY completed_at",
        (iso,),
    )
    tasks_overdue = query_all(
        conn,
        "SELECT * FROM tasks WHERE status != 'done' AND due_date IS NOT NULL "
        "AND due_date < ? ORDER BY due_date",
        (iso,),
    )
    memories_added = query_all(
        conn,
        "SELECT * FROM memories WHERE date(created_at) = ? ORDER BY created_at",
        (iso,),
    )

    estimated_minutes = sum(int(t["estimated_minutes"] or 0) for t in tasks_due)

    return {
        "kind": "daily",
        "date": iso,
        "generated_at": _now_iso(),
        # Recorded facts
        "tasks_due": [_task_summary(t) for t in tasks_due],
        "tasks_completed": [_task_summary(t) for t in tasks_completed],
        "tasks_overdue": [_task_summary(t) for t in tasks_overdue],
        "memories_added": [_memory_summary(m) for m in memories_added],
        "memories_added_approved": sum(
            1 for m in memories_added if bool(m["approved"])
        ),
        # Estimates (clearly labeled)
        "estimate_total_due_minutes": estimated_minutes,
        "estimate_note": (
            "estimated_minutes is a planning estimate, not measured time."
        ),
    }


# ---------------------------------------------------------------------------
# Weekly report
# ---------------------------------------------------------------------------

def weekly_report(conn, week_start: Optional[date] = None) -> dict:
    """Return a report for a Monday-start week (defaults to this week).

    Recorded facts come from the database.  Estimates are explicitly labeled.
    """
    start = week_start or _start_of_week(date.today())
    end = start + timedelta(days=6)
    iso_start, iso_end = _iso(start), _iso(end)

    tasks_completed = query_all(
        conn,
        "SELECT * FROM tasks WHERE status = 'done' AND completed_at IS NOT NULL "
        "AND date(completed_at) >= ? AND date(completed_at) <= ? "
        "ORDER BY completed_at",
        (iso_start, iso_end),
    )
    tasks_due_week = query_all(
        conn,
        "SELECT * FROM tasks WHERE due_date IS NOT NULL AND due_date >= ? "
        "AND due_date <= ? ORDER BY due_date",
        (iso_start, iso_end),
    )
    tasks_overdue = query_all(
        conn,
        "SELECT * FROM tasks WHERE status != 'done' AND due_date IS NOT NULL "
        "AND due_date < ? ORDER BY due_date",
        (iso_start,),
    )
    memories_added = query_all(
        conn,
        "SELECT * FROM memories WHERE date(created_at) >= ? AND date(created_at) "
        "<= ? ORDER BY created_at",
        (iso_start, iso_end),
    )
    projects = query_all(
        conn, "SELECT * FROM projects ORDER BY updated_at DESC"
    )

    estimated_minutes = sum(int(t["estimated_minutes"] or 0) for t in tasks_due_week)

    return {
        "kind": "weekly",
        "week_start": iso_start,
        "week_end": iso_end,
        "generated_at": _now_iso(),
        # Recorded facts
        "tasks_completed": [_task_summary(t) for t in tasks_completed],
        "tasks_completed_count": len(tasks_completed),
        "tasks_due_week": [_task_summary(t) for t in tasks_due_week],
        "tasks_overdue": [_task_summary(t) for t in tasks_overdue],
        "tasks_overdue_count": len(tasks_overdue),
        "memories_added": [_memory_summary(m) for m in memories_added],
        "projects": [
            {
                "id": p["id"],
                "title": p["title"],
                "status": p["status"],
            }
            for p in projects
        ],
        # Estimates
        "estimate_total_due_minutes": estimated_minutes,
        "estimate_note": (
            "estimated_minutes is a planning estimate, not measured time."
        ),
    }


__all__ = ["daily_report", "weekly_report"]

