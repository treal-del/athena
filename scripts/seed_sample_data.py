"""Seed Athena with clearly fictional sample data.

All names, companies, and details below are made up and contain no real
personal information.  Run this against a fresh database:

    python scripts/seed_sample_data.py

It uses the database configured in your environment (ATHENA_DATA_DIR /
ATHENA_DB_NAME), defaulting to ./data/athena.db.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly from the scripts/ folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta

from athena.config import DB_PATH
from athena.database import connect, init_db
from athena.domain import memory_service, project_service, task_service
from athena.models import (
    FixedCommitment,
    MemoryCreate,
    MilestoneCreate,
    NoteCreate,
    ProjectCreate,
    TaskCreate,
)

TODAY = date.today()


def main() -> None:
    init_db()
    conn = connect(DB_PATH)
    try:
        # ----- sample tasks (fictional) -----
        task_service.create_task(
            conn,
            TaskCreate(
                title="Draft Q3 plan for Sample Co project",
                description="Outline objectives for the fictional Sample Co engagement.",
                priority="high",
                estimated_minutes=90,
                due_date=(TODAY + timedelta(days=2)).isoformat(),
                status="todo",
            ),
        )
        task_service.create_task(
            conn,
            TaskCreate(
                title="Review sample expense report",
                description="Check the example expense spreadsheet.",
                priority="medium",
                estimated_minutes=30,
                due_date=TODAY.isoformat(),
                status="in_progress",
            ),
        )
        task_service.create_task(
            conn,
            TaskCreate(
                title="Call sample vendor (555-0100)",
                description="Fictional vendor call; 555 numbers are reserved for examples.",
                priority="low",
                estimated_minutes=15,
                due_date=(TODAY + timedelta(days=5)).isoformat(),
                status="todo",
            ),
        )
        task_service.create_task(
            conn,
            TaskCreate(
                title="Update sample documentation",
                description="Refresh the example README.",
                priority="medium",
                estimated_minutes=45,
                due_date=(TODAY - timedelta(days=1)).isoformat(),
                status="done",
            ),
        )

        # ----- sample fixed commitment -----
        conn.execute(
            "INSERT INTO fixed_commitments (title, start_dt, end_dt, source) "
            "VALUES (?, ?, ?, ?)",
            (
                "Sample team standup (example)",
                f"{TODAY.isoformat()}T09:00:00",
                f"{TODAY.isoformat()}T09:30:00",
                "sample",
            ),
        )
        conn.commit()

        # ----- sample memories (unapproved by default) -----
        memory_service.create_memory(
            conn,
            MemoryCreate(
                kind="profile_fact",
                content="Sample user prefers morning deep work.",
                source="onboarding example",
                approved=True,
            ),
        )
        memory_service.create_memory(
            conn,
            MemoryCreate(
                kind="goal",
                content="Launch the Sample Co demo by end of quarter.",
                source="planning example",
                approved=False,
            ),
        )
        memory_service.create_memory(
            conn,
            MemoryCreate(
                kind="knowledge_note",
                content="Example meeting note: discussed fictional roadmap.",
                source="sample meeting",
                approved=True,
            ),
        )

        # ----- sample project with milestone, task, note -----
        project = project_service.create_project(
            conn,
            ProjectCreate(
                title="Sample Co website redesign (example)",
                description="Fictional project for demonstration only.",
                status="active",
            ),
        )
        project_service.create_milestone(
            conn,
            MilestoneCreate(
                project_id=project.id,
                title="Sample wireframes",
                due_date=(TODAY + timedelta(days=7)).isoformat(),
                status="upcoming",
            ),
        )
        project_service.create_note(
            conn,
            NoteCreate(
                project_id=project.id,
                content="Sample note: all client names in this seed are fictional.",
            ),
        )
        task_service.create_task(
            conn,
            TaskCreate(
                title="Sample Co homepage mockup",
                description="Fictional design task linked to the sample project.",
                priority="medium",
                estimated_minutes=60,
                due_date=(TODAY + timedelta(days=3)).isoformat(),
                status="todo",
                project_id=project.id,
            ),
        )

        print(f"Sample data seeded into {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
