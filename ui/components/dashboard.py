"""Dashboard page: today's commitments, overdue tasks, upcoming deadlines,
recent progress."""

from __future__ import annotations

import streamlit as st

from athena.database import connect
from athena.domain import task_service
from athena.domain import memory_service
from athena.models import TaskUpdate
from athena.reporting import daily_report


def dashboard_page() -> None:
    _page_header("Dashboard")

    conn = connect()
    try:
        today_tasks = task_service.get_today_tasks(conn)
        overdue = task_service.get_overdue_tasks(conn)
        due_soon = task_service.get_due_soon(conn, days=3)
        report = daily_report(conn)
    finally:
        conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasks due today", len(today_tasks))
    c2.metric("Overdue tasks", len(overdue))
    c3.metric("Due in next 3 days", len(due_soon))
    c4.metric("Completed today", len(report["tasks_completed"]))

    st.divider()

    # Overdue
    st.markdown("### \u26a0\ufe0f Overdue tasks")
    if not overdue:
        st.info("No overdue tasks. \u2705")
    else:
        for t in overdue:
            with st.container(border=True):
                st.write(f"**{t.title}**")
                st.caption(
                    f"Priority: {t.priority} \u00b7 Due: {t.due_date} \u00b7 "
                    f"Estimated: {t.estimated_minutes} min"
                )

    st.divider()

    # Due today
    st.markdown("### \u23f1\ufe0f Due today")
    if not today_tasks:
        st.info("Nothing due today.")
    else:
        for t in today_tasks:
            with st.container(border=True):
                done = t.status == "done"
                checked = st.checkbox(
                    t.title,
                    value=done,
                    key=f"dashboard_done_{t.id}",
                )
                if checked != done:
                    new_status = "done" if checked else "todo"
                    conn = connect()
                    try:
                        task_service.update_task(
                            conn,
                            t.id,
                            TaskUpdate(status=new_status),
                        )
                    finally:
                        conn.close()
                    st.rerun()
                st.caption(
                    f"Priority: {t.priority} \u00b7 Estimated: {t.estimated_minutes} min"
                )

    st.divider()

    # Due soon
    st.markdown("### \u23f0 Upcoming deadlines (next 3 days)")
    if not due_soon:
        st.info("No upcoming deadlines.")
    else:
        for t in due_soon:
            with st.container(border=True):
                st.write(f"**{t.title}** \u00b7 Due {t.due_date}")
                st.caption(
                    f"Status: {t.status} \u00b7 Priority: {t.priority} "
                    f"\u00b7 Estimated: {t.estimated_minutes} min"
                )

    st.divider()

    # Recent progress / completed today
    st.markdown("### \u2705 Recent progress (completed today)")
    if not report["tasks_completed"]:
        st.info("No tasks completed today.")
    else:
        for t in report["tasks_completed"]:
            st.write(f"\u2714 {t['title']}")


def _page_header(title: str) -> None:
    st.subheader(title)
    st.divider()
