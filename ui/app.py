"""Athena — Streamlit entry point.

The UI only handles presentation and user input.  All database access and
business logic live in :mod:`athena.database` and the :mod:`athena.domain`
services; the UI never executes raw SQL.
"""

from __future__ import annotations

import streamlit as st

from athena.config import DB_PATH, DB_VERSION
from athena.database import connect, init_db
from athena.ai import load_provider
from ui.components import (
    dashboard_page,
    tasks_page,
    schedule_page,
    memory_page,
    projects_page,
    reports_page,
    export_page,
    settings_page,
)


def _ensure_db() -> None:
    """Initialize the database schema on startup."""
    init_db()


def _page_container(title: str):
    st.subheader(title)
    st.divider()


PAGES = {
    "Dashboard": dashboard_page,
    "Task Manager": tasks_page,
    "Schedule Planner": schedule_page,
    "Memory": memory_page,
    "Projects": projects_page,
    "Reports": reports_page,
    "Export / Backup": export_page,
    "Settings": settings_page,
}


def main() -> None:
    st.set_page_config(
        page_title="Athena — Personal AI Assistant",
        page_icon="\u2696\ufe0f",
        layout="wide",
    )

    _ensure_db()

    with st.sidebar:
        st.title("\u2696\ufe0f Athena")
        st.caption("Personal AI Assistant v0.1 — local-first")
        st.write(f"Database: `{DB_PATH}`")
        st.write(f"Schema version: `{DB_VERSION}`")
        st.divider()
        selection = st.radio("Navigate", list(PAGES.keys()), index=0)
        st.divider()
        st.markdown(
            "**v0.1 limitations:** no AI provider configured by default. "
            "Athena never fakes intelligence. "
            "All data stays in a local SQLite database."
        )

    page_fn = PAGES[selection]
    page_fn()


if __name__ == "__main__":
    main()
