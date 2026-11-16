"""Tests for reporting: daily/weekly reports built from real DB records."""

from __future__ import annotations

from datetime import date, timedelta

from athena.domain import task_service, memory_service
from athena.reporting import daily_report, weekly_report
from athena.models import MemoryCreate, TaskCreate, TaskUpdate


def test_daily_report_uses_real_records(conn):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    task_service.create_task(
        conn, TaskCreate(title="Due today", due_date=today, estimated_minutes=30)
    )
    task_service.create_task(
        conn, TaskCreate(title="Done today", status="done", due_date=yesterday,
                         estimated_minutes=20)
    )
    # mark Done today completed today
    all_tasks = task_service.list_tasks(conn)
    done_t = [t for t in all_tasks if t.title == "Done today"][0]
    task_service.update_task(conn, done_t.id, TaskUpdate(status="done"))

    memory_service.create_memory(
        conn, MemoryCreate(kind="goal", content="Fact", source="user", approved=True)
    )

    report = daily_report(conn)
    assert report["kind"] == "daily"
    assert report["date"] == today
    titles = {t["title"] for t in report["tasks_due"]}
    assert "Due today" in titles
    assert any(t["title"] == "Done today" for t in report["tasks_completed"])
    # Recorded facts present
    assert len(report["memories_added"]) >= 1
    # Estimates clearly labeled
    assert "estimate_note" in report
    assert "estimate" in report["estimate_note"].lower()
    assert isinstance(report["estimate_total_due_minutes"], int)


def test_weekly_report_uses_real_records(conn):
    start = date.today()
    task_service.create_task(
        conn, TaskCreate(title="Week task", status="done", estimated_minutes=40)
    )
    report = weekly_report(conn, week_start=start)
    assert report["kind"] == "weekly"
    assert report["tasks_completed_count"] >= 1
    assert "estimate_note" in report
    assert "estimated_minutes is a planning estimate" in report["estimate_note"]
