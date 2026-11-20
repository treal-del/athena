"""Schedule planner page.

Respects fixed commitments, task durations, breaks, deadlines, and
user-defined availability.  Conflicting fixed events are surfaced explicitly;
the planner never silently schedules over them.
"""

from __future__ import annotations

from datetime import datetime, time

import streamlit as st

from athena.database import connect
from athena.domain import setting_service
from athena.domain import task_service
from athena.models import FixedCommitment, ScheduleResult
from athena.planning import Availability, schedule


def schedule_page() -> None:
    st.subheader("Schedule Planner")
    st.caption(
        "Plan tasks around fixed commitments. The planner detects conflicts "
        "and never schedules over a fixed event."
    )
    st.divider()

    conn = connect()
    try:
        commitments = [
            FixedCommitment(
                id=r["id"],
                title=r["title"],
                start_dt=r["start_dt"],
                end_dt=r["end_dt"],
                source=r["source"],
            )
            for r in conn.execute(
                "SELECT * FROM fixed_commitments ORDER BY start_dt"
            ).fetchall()
        ]
        tasks = task_service.list_tasks(conn)
    finally:
        conn.close()

    # ---- Fixed commitments --------------------------------------------
    st.markdown("### Fixed commitments")
    with st.expander("Add a fixed commitment", expanded=False):
        with st.form("add_commitment_form", clear_on_submit=True):
            c_title = st.text_input("Title *", max_chars=200)
            col1, col2 = st.columns(2)
            c_start = col1.datetime_input("Start", value=datetime.now())
            c_end = col2.datetime_input("End", value=datetime.now())
            c_source = st.text_input("Source (optional)", max_chars=500)
            c_submitted = st.form_submit_button("Add commitment")
            if c_submitted:
                if not c_title.strip():
                    st.error("Title is required.")
                elif c_end <= c_start:
                    st.error("End must be after start.")
                else:
                    conn = connect()
                    try:
                        conn.execute(
                            "INSERT INTO fixed_commitments (title, start_dt, end_dt, source) "
                            "VALUES (?, ?, ?, ?)",
                            (
                                c_title.strip(),
                                c_start.isoformat(),
                                c_end.isoformat(),
                                c_source.strip() or None,
                            ),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    st.success("Commitment added.")
                    st.rerun()

    if commitments:
        for c in commitments:
            with st.container(border=True):
                st.write(f"**{c.title}**")
                st.caption(
                    f"{c.start_dt[:16]} \u2013 {c.end_dt[:16]}"
                    + (f" \u00b7 source: {c.source}" if c.source else "")
                )
    else:
        st.info("No fixed commitments yet.")

    st.divider()

    # ---- Availability --------------------------------------------------
    st.markdown("### Your availability")
    st.caption(
        "Defaults are loaded from Settings. Adjust below for this planning run."
    )

    conn = connect()
    try:
        saved = setting_service.get_availability(conn)
    finally:
        conn.close()

    colA, colB, colC, colD = st.columns(4)
    work_start = colA.time_input(
        "Work day starts", value=saved.work_start, key="sched_work_start"
    )
    work_end = colB.time_input(
        "Work day ends", value=saved.work_end, key="sched_work_end"
    )
    lunch_start = colC.time_input(
        "Lunch starts",
        value=saved.lunch_start or time(12, 0),
        key="sched_lunch_start",
    )
    lunch_end = colD.time_input(
        "Lunch ends",
        value=saved.lunch_end or time(13, 0),
        key="sched_lunch_end",
    )

    availability = Availability(
        work_start=work_start,
        work_end=work_end,
        lunch_start=lunch_start,
        lunch_end=lunch_end,
    )

    st.divider()

    # ---- Generate schedule --------------------------------------------
    st.markdown("### Generate schedule")
    planning_days = st.number_input(
        "Planning window (days)", min_value=1, max_value=30, value=7, step=1
    )
    if st.button("Build schedule", type="primary"):
        result = schedule(
            tasks, commitments, availability=availability,
            planning_days=int(planning_days),
        )
        st.session_state["athena_schedule"] = result

    result = st.session_state.get("athena_schedule")
    if isinstance(result, ScheduleResult):
        _render_schedule(result)


def _render_schedule(result: ScheduleResult) -> None:
    st.divider()
    st.markdown("### Schedule")
    if result.conflicts:
        st.error("Conflicts detected:")
        for conflict in result.conflicts:
            st.write(f"\u26a0\ufe0f {conflict}")
    if result.unscheduled:
        st.warning(
            "Some tasks could not be fully scheduled before their deadline: "
            + ", ".join(str(i) for i in result.unscheduled)
        )
    if not result.blocks:
        st.info("No schedule blocks generated.")
        return

    for block in result.blocks:
        kind_emoji = {
            "commitment": "\u26a0\ufe0f",
            "task": "\u23f1\ufe0f",
            "break": "\u231a\ufe0f",
        }.get(block.kind, "\u25cf")
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 2])
            c1.write(f"{kind_emoji} **{block.title}**")
            c2.caption(block.start[:16])
            c3.caption(block.end[:16] + f"  ({block.kind})")
            if block.kind == "task" and block.task_id:
                st.caption(f"Task id: {block.task_id}")
            elif block.kind == "commitment" and block.commitment_id:
                st.caption(f"Commitment id: {block.commitment_id}")
