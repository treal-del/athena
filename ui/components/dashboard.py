"""Dashboard page: today's commitments, overdue tasks, upcoming deadlines,
recent progress, and weekly charts."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import streamlit as st

from athena.database import connect
from athena.domain import task_service
from athena.domain import memory_service
from athena.models import TaskUpdate
from athena.reporting import daily_report


def _completion_counts_by_day(conn, days: int = 7):
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = conn.execute(
        """
        SELECT date(completed_at) as day, COUNT(*) as cnt
        FROM tasks
        WHERE status = 'done' AND completed_at IS NOT NULL
          AND date(completed_at) >= ? AND date(completed_at) <= ?
        GROUP BY date(completed_at)
        ORDER BY day
        """,
        (start.isoformat(), today.isoformat()),
    ).fetchall()
    counts = {r["day"]: r["cnt"] for r in rows}
    result = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        result.append((d, counts.get(d, 0)))
    return result


def _top_priorities(conn, limit: int = 3):
    tasks = task_service.list_tasks(conn)
    incomplete = [t for t in tasks if t.status != "done"]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    incomplete.sort(key=lambda t: (order.get(t.priority, 4), t.due_date or ""))
    return incomplete[:limit]


def dashboard_page() -> None:
    _page_header("Dashboard")

    conn = connect()
    try:
        today_tasks = task_service.get_today_tasks(conn)
        overdue = task_service.get_overdue_tasks(conn)
        due_soon = task_service.get_due_soon(conn, days=3)
        report = daily_report(conn)
        completion = _completion_counts_by_day(conn)
        top_priorities = _top_priorities(conn)
    finally:
        conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasks due today", len(today_tasks))
    c2.metric("Overdue tasks", len(overdue))
    c3.metric("Due in next 3 days", len(due_soon))
    c4.metric("Completed today", len(report["tasks_completed"]))

    st.divider()

    # ---- Weekly progress chart ----------------------------------------
    st.markdown("### 📈 Weekly progress (completed tasks)")
    if sum(c for _, c in completion) == 0:
        st.info("No tasks completed this week yet.")
    else:
        chart_data = {d: c for d, c in completion}
        st.bar_chart(chart_data, height=200)
        st.caption("Tasks completed per day over the last 7 days.")

    st.divider()

    # ---- Top priorities -----------------------------------------------
    st.markdown("### 🔴 Top priorities")
    if not top_priorities:
        st.info("No high-priority tasks pending.")
    else:
        for t in top_priorities:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                t.priority, "⚪"
            )
            with st.container(border=True):
                st.write(f"{emoji} **{t.title}**")
                st.caption(
                    f"Priority: {t.priority} · Due: {t.due_date or '—'} "
                    f"· Estimated: {t.estimated_minutes} min"
                )

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
