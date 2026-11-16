"""Tests for task domain operations."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from athena.domain import task_service
from athena.models import TaskCreate, TaskUpdate


def _make(conn, **kwargs):
    data = dict(
        title="Task",
        description="",
        priority="medium",
        estimated_minutes=30,
        due_date=None,
        status="todo",
    )
    data.update(kwargs)
    return task_service.create_task(conn, TaskCreate(**data))


def test_create_and_get_task(conn):
    t = _make(conn, title="Buy groceries", priority="high", estimated_minutes=15,
              due_date="2024-02-01")
    assert t.id is not None
    assert t.title == "Buy groceries"
    assert t.priority == "high"
    assert t.status == "todo"
    assert t.completed_at is None
    fetched = task_service.get_task(conn, t.id)
    assert fetched is not None
    assert fetched.title == "Buy groceries"


def test_get_task_missing(conn):
    assert task_service.get_task(conn, 12345) is None


def test_update_task(conn):
    t = _make(conn)
    updated = task_service.update_task(
        conn, t.id, TaskUpdate(status="in_progress", priority="high")
    )
    assert updated.status == "in_progress"
    assert updated.priority == "high"
    assert updated.completed_at is None  # not done yet

    done = task_service.update_task(conn, t.id, TaskUpdate(status="done"))
    assert done.status == "done"
    assert done.completed_at is not None  # completion timestamp set

    reopened = task_service.update_task(conn, t.id, TaskUpdate(status="todo"))
    assert reopened.status == "todo"
    assert reopened.completed_at is None  # cleared


def test_delete_task(conn):
    t = _make(conn)
    assert task_service.delete_task(conn, t.id) is True
    assert task_service.get_task(conn, t.id) is None
    assert task_service.delete_task(conn, t.id) is False


def test_list_tasks_filters(conn):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _make(conn, title="Overdue", status="todo", due_date=yesterday)
    _make(conn, title="Done", status="done", due_date=yesterday)
    _make(conn, title="Today", status="todo", due_date=today)

    overdue = task_service.get_overdue_tasks(conn)
    assert len(overdue) == 1
    assert overdue[0].title == "Overdue"

    today_tasks = task_service.get_today_tasks(conn)
    assert len(today_tasks) == 1
    assert today_tasks[0].title == "Today"

    done = task_service.list_tasks(conn, status="done")
    assert len(done) == 1
    assert done[0].title == "Done"


def test_due_soon(conn):
    soon = (date.today() + timedelta(days=2)).isoformat()
    late = (date.today() + timedelta(days=10)).isoformat()
    _make(conn, title="Soon", status="todo", due_date=soon)
    _make(conn, title="Late", status="todo", due_date=late)
    _make(conn, title="Done soon", status="done", due_date=soon)

    due = task_service.get_due_soon(conn, days=3)
    titles = {t.title for t in due}
    assert "Soon" in titles
    assert "Late" not in titles
    assert "Done soon" not in titles


def test_invalid_input_rejected(conn):
    with pytest.raises(Exception):
        task_service.create_task(
            conn, TaskCreate(title="", priority="bogus")
        )
