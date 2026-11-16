"""Tests for the deterministic schedule planner.

Covered: fixed-commitment conflict detection, duration/deadline/availability
respect, and that scheduled tasks never overlap fixed events.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from athena.models import FixedCommitment, Task
from athena.planning import Availability, schedule


def _task(tid, title, minutes, due=None, priority="medium"):
    return Task(
        id=tid,
        title=title,
        description="",
        priority=priority,
        estimated_minutes=minutes,
        due_date=due,
        status="todo",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        completed_at=None,
        project_id=None,
    )


def _commitment(cid, title, start, end, source="test"):
    return FixedCommitment(
        id=cid, title=title, start_dt=start, end_dt=end, source=source
    )


def _today_iso(dt: datetime) -> str:
    return dt.date().isoformat()


def _future_iso() -> str:
    return (datetime.now().date() + timedelta(days=1)).isoformat()


def test_schedule_respects_availability_and_no_conflicts():
    due = _future_iso()
    tasks = [_task(1, "Write report", 60, due=due)]
    commitments = []
    result = schedule(tasks, commitments)
    assert result.unscheduled == []
    assert result.conflicts == []
    assert any(b.kind == "task" and b.task_id == 1 for b in result.blocks)
    # Task block falls within work hours (default 09:00-17:00).
    tb = [b for b in result.blocks if b.kind == "task"][0]
    start = datetime.fromisoformat(tb.start).time()
    end = datetime.fromisoformat(tb.end).time()
    assert start >= time(9, 0)
    assert end <= time(17, 0)


def test_detects_overlapping_fixed_commitments():
    today = datetime.now().date().isoformat()
    start = f"{today}T10:00:00"
    end = f"{today}T11:00:00"
    commitments = [
        _commitment(1, "Meeting A", start, end),
        _commitment(2, "Meeting B", f"{today}T10:30:00", f"{today}T11:30:00"),
    ]
    result = schedule([], commitments)
    assert any("overlap" in c.lower() for c in result.conflicts)


def test_never_schedules_over_a_fixed_commitment():
    due = _future_iso()
    commitments = [
        _commitment(1, "Meeting", f"{due}T10:00:00", f"{due}T11:00:00")
    ]
    tasks = [_task(1, "Task", 30, due=due)]
    result = schedule(tasks, commitments)
    assert result.unscheduled == []
    task_block = [b for b in result.blocks if b.kind == "task"][0]
    tb_start = datetime.fromisoformat(task_block.start)
    tb_end = datetime.fromisoformat(task_block.end)
    meeting_start = datetime.fromisoformat(f"{due}T10:00:00")
    meeting_end = datetime.fromisoformat(f"{due}T11:00:00")
    # No overlap with the fixed meeting.
    assert not (tb_start < meeting_end and meeting_start < tb_end)


def test_task_unable_to_fit_before_deadline_is_unscheduled():
    today = datetime.now().date().isoformat()
    # 2000 minutes due today cannot fit in a single work day.
    tasks = [_task(1, "Huge task", 2000, due=today)]
    result = schedule(tasks, [])
    assert 1 in result.unscheduled
    assert any("Huge task" in c for c in result.conflicts)


def test_breaks_are_inserted():
    due = _future_iso()
    # Long task so a break triggers (default break every 120 min, 15 min long).
    tasks = [_task(1, "Long task", 200, due=due)]
    avail = Availability(work_start=time(9, 0), work_end=time(17, 0))
    result = schedule(tasks, [], availability=avail)
    assert any(b.kind == "break" for b in result.blocks), result.blocks


def test_empty_input_returns_empty_result():
    result = schedule([], [])
    assert result.blocks == []
    assert result.conflicts == []
    assert result.unscheduled == []
