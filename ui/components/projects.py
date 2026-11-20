"""Projects page: list of projects with links to project detail pages."""

from __future__ import annotations

import streamlit as st

from athena.database import connect
from athena.domain import project_service
from athena.models import ProjectCreate
from ui.components.project_detail import render_project_card, project_detail_page


def projects_page() -> None:
    # If a project_id is in query params, show the project detail page.
    if st.query_params.get("project_id") is not None:
        project_detail_page()
        return

    st.subheader("Projects")
    st.caption(
        "Track projects with milestones, linked tasks, notes, and status. "
        "Click 'View' on a project to open its detail page."
    )
    st.divider()

    conn = connect()
    try:
        projects = project_service.list_projects(conn)
    finally:
        conn.close()

    # ---- Add project ---------------------------------------------------
    with st.expander("Add a new project", expanded=False):
        with st.form("add_project_form", clear_on_submit=True):
            p_title = st.text_input("Title *", max_chars=200)
            p_description = st.text_area("Description", max_chars=4000)
            p_status = st.selectbox(
                "Status",
                ["planning", "active", "on_hold", "completed", "archived"],
                index=1,
            )
            p_submitted = st.form_submit_button("Create project")
            if p_submitted:
                if not p_title.strip():
                    st.error("Title is required.")
                else:
                    conn = connect()
                    try:
                        project_service.create_project(
                            conn,
                            ProjectCreate(
                                title=p_title.strip(),
                                description=p_description,
                                status=p_status,
                            ),
                        )
                    finally:
                        conn.close()
                    st.success("Project created.")
                    st.rerun()

    st.divider()

    if not projects:
        st.info("No projects yet. Create your first project above.")
        return

    for p in projects:
        render_project_card(conn, p)