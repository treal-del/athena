"""Settings domain logic.

Handles user-configurable preferences such as planner availability
(work hours, lunch, breaks).  Stored in the ``availability_settings``
table so they persist across application restarts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from ..database import connect, execute, query_one
from ..planning.scheduler import Availability


@dataclass
class AvailabilitySettings:
    """Persisted availability preferences."""

    work_start: time = time(9, 0)
    work_end: time = time(17, 0)
    lunch_start: time | None = time(12, 0)
    lunch_end: time | None = time(13, 0)
    break_every_minutes: int = 120
    break_duration_minutes: int = 15

    def to_planning_availability(self) -> Availability:
        return Availability(
            work_start=self.work_start,
            work_end=self.work_end,
            lunch_start=self.lunch_start,
            lunch_end=self.lunch_end,
            break_every_minutes=self.break_every_minutes,
            break_duration_minutes=self.break_duration_minutes,
        )


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    parts = value.split(":")
    return time(int(parts[0]), int(parts[1]))


def _row_to_settings(row) -> AvailabilitySettings:
    return AvailabilitySettings(
        work_start=_parse_time(row["work_start"]),
        work_end=_parse_time(row["work_end"]),
        lunch_start=_parse_time(row["lunch_start"]),
        lunch_end=_parse_time(row["lunch_end"]),
        break_every_minutes=row["break_every_minutes"],
        break_duration_minutes=row["break_duration_minutes"],
    )


def get_availability(conn) -> AvailabilitySettings:
    """Return the current availability settings (creating defaults if missing)."""
    row = query_one(
        conn,
        "SELECT * FROM availability_settings WHERE id = 1",
    )
    if row is None:
        now = datetime.utcnow().isoformat()
        execute(
            conn,
            """
            INSERT INTO availability_settings
                (id, work_start, work_end, lunch_start, lunch_end,
                 break_every_minutes, break_duration_minutes, updated_at)
            VALUES (1, '09:00', '17:00', '12:00', '13:00', 120, 15, ?)
            """,
            (now,),
        )
        row = query_one(
            conn, "SELECT * FROM availability_settings WHERE id = 1"
        )
    return _row_to_settings(row)


def save_availability(conn, settings: AvailabilitySettings) -> None:
    """Persist availability settings."""
    now = datetime.utcnow().isoformat()
    execute(
        conn,
        """
        UPDATE availability_settings
        SET work_start = ?, work_end = ?, lunch_start = ?, lunch_end = ?,
            break_every_minutes = ?, break_duration_minutes = ?,
            updated_at = ?
        WHERE id = 1
        """,
        (
            settings.work_start.isoformat(),
            settings.work_end.isoformat(),
            settings.lunch_start.isoformat() if settings.lunch_start else None,
            settings.lunch_end.isoformat() if settings.lunch_end else None,
            settings.break_every_minutes,
            settings.break_duration_minutes,
            now,
        ),
    )


__all__ = ["get_availability", "save_availability", "AvailabilitySettings"]
