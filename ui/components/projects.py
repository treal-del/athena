"""Projects page: milestones, tasks, notes, and status."""

from __future__ import annotations

import streamlit as st

from athena.database import connect
from athena.domain import project_service
from athena.models import (
    MilestoneCreate,
    NoteCreate,
    ProjectCreate,
    ProjectUpdate,
    TaskCreate,
    TaskUpdate,
)


def projects_page() -> None:
    st.subheader("Projects")
    st.caption(
        "Track projects with milestones, linked tasks, notes, and status."
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
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{p.title}**")
            c2.caption(f"Status: {p.status}")
            c3.caption(f"Updated: {p.updated_at[:10]}")
            if p.description:
                st.caption(p.description)

            b1, b2, _ = st.columns([1, 1, 6])
            if b1.button("Edit", key=f"edit_proj_{p.id}"):
                st.session_state[f"editing_proj_{p.id}"] = True
            if b2.button("Delete", key=f"del_proj_{p.id}", type="secondary"):
                conn = connect()
                try:
                    project_service.delete_project(conn, p.id)
                finally:
                    conn.close()
                    st.success("Project deleted.")
                    st.rerun()

            if st.session_state.get(f"editing_proj_{p.id}"):
                _render_project_edit(conn, p.id)

            st.markdown("**Milestones**")
            _render_milestones(conn, p.id)

            st.markdown("**Linked tasks**")
            _render_project_tasks(conn, p.id)

            st.markdown("**Notes**")
            _render_notes(conn, p.id)


def _render_project_edit(conn, project_id: int) -> None:
    project = project_service.get_project(conn, project_id)
    if project is None:
        st.error("Project not found.")
        return
    with st.form(f"edit_proj_form_{project_id}"):
        title = st.text_input("Title", value=project.title, max_chars=200)
        description = st.text_area(
            "Description", value=project.description, max_chars=4000
        )
        status = st.selectbox(
            "Status",
            ["planning", "active", "on_hold", "completed", "archived"],
            index=["planning", "active", "on_hold", "completed", "archived"].index(
                project.status
            ),
        )
        col_save, col_cancel = st.columns([1, 1])
        save = col_save.form_submit_button("Save changes")
        cancel = col_cancel.form_submit_button("Cancel")
        if cancel:
            st.session_state[f"editing_proj_{project_id}"] = False
            st.rerun()
        if save:
            if not title.strip():
                st.error("Title is required.")
                return
            project_service.update_project(
                conn,
                project_id,
                ProjectUpdate(
                    title=title.strip(),
                    description=description,
                    status=status,
                ),
            )
            st.session_state[f"editing_proj_{project_id}"] = False
            st.success("Project updated.")
            st.rerun()


def _render_milestones(conn, project_id: int) -> None:
    milestones = project_service.list_milestones(conn, project_id)
    with st.form(f"add_milestone_form_{project_id}", clear_on_submit=True):
        col1, col2, col3 = st.columns([3, 2, 1])
        m_title = col1.text_input("Milestone title", max_chars=200)
        m_due = col2.date_input("Due date", value=None)
        m_status = col3.selectbox(
            "Status", ["upcoming", "in_progress", "done", "cancelled"], index=0
        )
        added = st.form_submit_button("Add milestone")
        if added:
            if not m_title.strip():
                st.error("Title is required.")
            else:
                due = m_due.isoformat() if m_due else None
                project_service.create_milestone(
                    conn,
                    MilestoneCreate(
                        project_id=project_id,
                        title=m_title.strip(),
                        due_date=due,
                        status=m_status,
                    ),
                )
                st.success("Milestone added.")
                st.rerun()
    for ms in milestones:
        line = "\u2022 " + ms.title
        if ms.due_date:
            line += f" (due {ms.due_date})"
        line += f" \u00b7 {ms.status}"
        st.write(line)


def _render_project_tasks(conn, project_id: int) -> None:
    tasks = task_service.list_tasks(conn, project_id=project_id)
    if not tasks:
        st.info("No tasks linked to this project.")
        return
    for t in tasks:
        done = t.status == "done"
        checked = st.checkbox(
            f"**{t.title}**", value=done, key=f"proj_task_done_{t.id}"
        )
        if checked != done:
            new_status = "done" if checked else "todo"
            task_service.update_task(
                conn, t.id, TaskUpdate(status=new_status)
            )
            st.rerun()
        st.caption(f"Status: {t.status} \u00b7 Priority: {t.priority} \u00b7 {t.estimated_minutes} min")


def _render_notes(conn, project_id: int) -> None:
    notes = project_service.list_notes(conn, project_id)
    with st.form(f"add_note_form_{project_id}", clear_on_submit=True):
        n_content = st.text_area("New note", max_chars=4000)
        added = st.form_submit_button("Add note")
        if added:
            if not n_content.strip():
                st.error("Content is required.")
            else:
                project_service.create_note(
                    conn, NoteCreate(project_id=project_id, content=n_content.strip())
                )
                st.success("Note added.")
                st.rerun()
    for n in notes:
        st.write("\u2022 " + n.content)
        st.caption(n.created_at[:16])

