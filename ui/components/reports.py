"""Reports page: daily and weekly reports from real database records."""

from __future__ import annotations

from datetime import date

import streamlit as st

from athena.database import connect
from athena.reporting import daily_report, weekly_report


def reports_page() -> None:
    st.subheader("Reports")
    st.caption(
        "Reports are generated from actual database records. Recorded facts "
        "are separated from planning estimates."
    )
    st.divider()

    tab_daily, tab_weekly = st.tabs(["Daily report", "Weekly report"])

    with tab_daily:
        _daily_tab()

    with tab_weekly:
        _weekly_tab()


def _daily_tab() -> None:
    st.markdown("### Daily report")
    day = st.date_input("Date", value=date.today(), key="report_day")
    conn = connect()
    try:
        report = daily_report(conn, day)
    finally:
        conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks due", len(report["tasks_due"]))
    c2.metric("Tasks completed", len(report["tasks_completed"]))
    c3.metric("Tasks overdue", len(report["tasks_overdue"]))

    st.markdown("#### Recorded facts")
    st.write("**Tasks due:**")
    _render_task_list(report["tasks_due"])
    st.write("**Completed today:**")
    _render_task_list(report["tasks_completed"])
    st.write("**Overdue:**")
    _render_task_list(report["tasks_overdue"])
    st.write(
        f"Memories added: {len(report['memories_added'])} "
        f"({report['memories_added_approved']} approved)"
    )

    st.markdown("#### Estimates (not measured)")
    st.info(
        f"{report['estimate_note']} "
        f"Estimated minutes due today: {report['estimate_total_due_minutes']}"
    )


def _weekly_tab() -> None:
    st.markdown("### Weekly report")
    week_start = st.date_input(
        "Week starts (Monday)", value=date.today(), key="report_week"
    )
    conn = connect()
    try:
        report = weekly_report(conn, week_start)
    finally:
        conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks completed", report["tasks_completed_count"])
    c2.metric("Tasks due this week", len(report["tasks_due_week"]))
    c3.metric("Tasks overdue", report["tasks_overdue_count"])

    st.markdown("#### Recorded facts")
    st.write("**Completed this week:**")
    _render_task_list(report["tasks_completed"])
    st.write("**Due this week:**")
    _render_task_list(report["tasks_due_week"])
    st.write("**Overdue:**")
    _render_task_list(report["tasks_overdue"])
    st.write(
        f"Memories added: {len(report['memories_added'])}"
    )
    st.write("**Projects:**")
    for p in report["projects"]:
        st.write(f"\u2022 {p['title']} \u00b7 {p['status']}")

    st.markdown("#### Estimates (not measured)")
    st.info(
        f"{report['estimate_note']} "
        f"Estimated minutes due this week: {report['estimate_total_due_minutes']}"
    )


def _render_task_list(tasks) -> None:
    if not tasks:
        st.caption("\u2014 none \u2014")
        return
    for t in tasks:
        st.write(
            f"\u2022 {t['title']} \u00b7 status: {t['status']} \u00b7 "
            f"priority: {t['priority']} \u00b7 due: {t['due_date'] or '\u2014'} \u00b7 "
            f"est. {t['estimated_minutes']} min"
        )
