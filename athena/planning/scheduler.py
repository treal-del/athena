"""Deterministic schedule planner.

The planner builds a day-by-day schedule from:

* tasks (with estimated duration, due date, priority)
* fixed commitments (immutable appointments the planner must not move)
* user-defined availability (work hours, breaks, lunch)

It never silently schedules over a fixed event: any fixed-commitment overlap
or task that cannot be placed before its deadline is recorded as a conflict
and the task is listed as unscheduled.

All logic is deterministic and requires no AI model.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from dataclasses import dataclass
from typing import Optional, Sequence

from ..models import FixedCommitment, ScheduledBlock, ScheduleResult, Task


@dataclass
class Availability:
    """User-defined availability for each planning day."""

    work_start: time = time(9, 0)       # 09:00
    work_end: time = time(17, 0)        # 17:00
    lunch_start: Optional[time] = time(12, 0)
    lunch_end: Optional[time] = time(13, 0)
    break_every_minutes: int = 120      # short break every 2 hours
    break_duration_minutes: int = 15


def _combine(day: date, t: time) -> datetime:
    return datetime.combine(day, t)


def _overlaps(a_start: datetime, a_end: datetime,
              b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


def _priority_weight(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 2)


def schedule(
    tasks: Sequence[Task],
    fixed_commitments: Sequence[FixedCommitment],
    availability: Optional[Availability] = None,
    planning_days: int = 7,
) -> ScheduleResult:
    """Produce a schedule respecting commitments, durations, breaks, and deadlines.

    Returns a :class:`ScheduleResult`.  Tasks that cannot be placed before
    their deadline are added to ``unscheduled`` and described in
    ``conflicts``.  Overlapping fixed commitments are also reported as
    conflicts (they are never moved or dropped).
    """
    avail = availability or Availability()
    result = ScheduleResult()
    today = date.today()
    window_end = today + timedelta(days=planning_days - 1)

    # --- Normalize tasks -------------------------------------------------
    remaining = {t.id: int(t.estimated_minutes or 0) for t in tasks}
    task_by_id = {t.id: t for t in tasks}

    # Sort: due date first (None last), then priority, then created_at.
    def sort_key(t: Task):
        due = t.due_date
        due_sort = (0, due) if due else (1, "")
        return (due_sort, _priority_weight(t.priority), t.created_at)

    ordered = sorted(tasks, key=sort_key)

    # --- Detect fixed-commitment conflicts -------------------------------
    commitment_intervals = []  # (day, start, end, commitment)
    for c in fixed_commitments:
        try:
            c_start = datetime.fromisoformat(c.start_dt)
            c_end = datetime.fromisoformat(c.end_dt)
        except ValueError:
            continue
        commitment_intervals.append((c_start.date(), c_start, c_end, c))

    # Pairwise fixed-commitment overlaps are conflicts.
    for i in range(len(commitment_intervals)):
        for j in range(i + 1, len(commitment_intervals)):
            _, a_start, a_end, _ = commitment_intervals[i]
            _, b_start, b_end, _ = commitment_intervals[j]
            if _overlaps(a_start, a_end, b_start, b_end):
                result.conflicts.append(
                    "Fixed commitments overlap: '"
                    + commitment_intervals[i][3].title
                    + "' and '"
                    + commitment_intervals[j][3].title
                    + "'"
                )

    # --- Day-by-day placement -------------------------------------------
    busy: dict = {}
    for day_start, c_start, c_end, c in commitment_intervals:
        if today <= day_start <= window_end:
            busy.setdefault(day_start, []).append((c_start, c_end))
            result.blocks.append(ScheduledBlock(
                start=c_start.isoformat(),
                end=c_end.isoformat(),
                title=c.title,
                kind="commitment",
                commitment_id=c.id,
            ))

    def free_slots(day: date) -> list:
        """Return free (start, end) intervals within availability for a day."""
        ws = _combine(day, avail.work_start)
        we = _combine(day, avail.work_end)
        if we <= ws:
            return []
        blocked = list(busy.get(day, []))
        if avail.lunch_start and avail.lunch_end:
            blocked.append((_combine(day, avail.lunch_start),
                            _combine(day, avail.lunch_end)))
        blocked.sort()
        slots = []
        cursor = ws
        for b_start, b_end in blocked:
            b_start = max(b_start, ws)
            b_end = min(b_end, we)
            if b_start > cursor:
                slots.append((cursor, b_start))
            cursor = max(cursor, b_end)
        if cursor < we:
            slots.append((cursor, we))
        return slots

    def place_on_day(task: Task, day: date, minutes_needed: int) -> int:
        """Place up to ``minutes_needed`` of a task on ``day``. Returns minutes placed.

        Long blocks are split so continuous task work never exceeds
        ``break_every_minutes`` without a break.  Placement stays inside the
        free slots returned by :func:`free_slots` (which already excludes
        fixed commitments and lunch).
        """
        if minutes_needed <= 0:
            return 0
        placed = 0
        slots = free_slots(day)
        new_busy = list(busy.get(day, []))
        for slot_start, slot_end in slots:
            if placed >= minutes_needed:
                break
            if day == today:
                now = datetime.now()
                if slot_end <= now:
                    continue
                slot_start = max(slot_start, now)
            cursor = slot_start
            remaining_in_slot = min(
                minutes_needed - placed,
                int((slot_end - slot_start).total_seconds() // 60),
            )
            while remaining_in_slot > 0:
                slot_left_minutes = int((slot_end - cursor).total_seconds() // 60)
                if slot_left_minutes <= 0:
                    break
                chunk = min(remaining_in_slot, slot_left_minutes)
                if (
                    avail.break_every_minutes
                    and avail.break_duration_minutes > 0
                    and chunk > avail.break_every_minutes
                ):
                    chunk = avail.break_every_minutes
                block_start = cursor
                block_end = _add_minutes(block_start, chunk)
                result.blocks.append(ScheduledBlock(
                    start=block_start.isoformat(),
                    end=block_end.isoformat(),
                    title=task.title,
                    kind="task",
                    task_id=task.id,
                ))
                new_busy.append((block_start, block_end))
                placed += chunk
                remaining_in_slot -= chunk
                cursor = block_end
                # Insert a break only if more task work remains in this slot.
                if remaining_in_slot > 0:
                    slot_left_after = int((slot_end - cursor).total_seconds() // 60)
                    if slot_left_after > 0 and avail.break_duration_minutes > 0:
                        break_start = cursor
                        break_end = _add_minutes(
                            cursor, avail.break_duration_minutes
                        )
                        result.blocks.append(ScheduledBlock(
                            start=break_start.isoformat(),
                            end=break_end.isoformat(),
                            title="Break",
                            kind="break",
                        ))
                        new_busy.append((break_start, break_end))
                        cursor = break_end
        busy[day] = new_busy
        return placed

    # Place each task, splitting across days as needed, before its due date.
    for task in ordered:
        minutes_needed = remaining[task.id]
        if minutes_needed <= 0:
            continue

        due_date = None
        if task.due_date:
            try:
                due_date = date.fromisoformat(task.due_date)
            except ValueError:
                due_date = None

        placed_total = 0
        last_day = due_date if due_date else window_end
        if last_day < today:
            last_day = today
        current_day = today
        while current_day <= last_day and placed_total < minutes_needed:
            if current_day > window_end:
                break
            take = place_on_day(task, current_day, minutes_needed - placed_total)
            placed_total += take
            current_day += timedelta(days=1)

        remaining[task.id] = minutes_needed - placed_total
        if remaining[task.id] > 0:
            result.conflicts.append(
                "Task '" + task.title + "' (" + str(minutes_needed)
                + " min est.) could not be fully scheduled before its deadline "
                + "(" + (task.due_date or "no deadline")
                + ") within the planning window."
            )
            result.unscheduled.append(task.id)

    # Sort blocks chronologically.
    result.blocks.sort(key=lambda b: b.start)
    return result


__all__ = ["schedule", "Availability"]
