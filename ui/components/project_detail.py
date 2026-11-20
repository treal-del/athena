"""Project detail page: milestones, linked tasks, notes, and status for one project."""

from __future__ import annotations

from datetime import date

import streamlit as st

from athena.database import connect
from athena.domain import project_service, task_service
from athena.models import (
    MilestoneCreate,
    NoteCreate,
    ProjectUpdate,
    TaskCreate,
    TaskUpdate,
)


def project_detail_page() -> None:
    project_id = st.query_params.get("project_id")
    if project_id is None:
        st.error("No project selected.")
        if st.button("Go to Projects"):
            st.query_params.clear()
            st.rerun()
        return

    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        st.error("Invalid project id.")
        if st.button("Go to Projects"):
            st.query_params.clear()
            st.rerun()
        return

    conn = connect()
    try:
        project = project_service.get_project(conn, project_id)
    finally:
        conn.close()

    if project is None:
        st.error("Project not found.")
        if st.button("Go to Projects"):
            st.query_params.clear()
            st.rerun()
        return

    st.subheader(f"Project: {project.title}")
    st.caption(f"Status: {project.status} · Updated: {project.updated_at[:10]}")
    if project.description:
        st.write(project.description)
    st.divider()

    # Edit project
    with st.expander("Edit project", expanded=False):
        with st.form(f"edit_proj_form_{project_id}", clear_on_submit=True):
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
                st.query_params.clear()
                st.rerun()
            if save:
                if not title.strip():
                    st.error("Title is required.")
                else:
                    conn = connect()
                    try:
                        project_service.update_project(
                            conn,
                            project_id,
                            ProjectUpdate(
                                title=title.strip(),
                                description=description,
                                status=status,
                            ),
                        )
                    finally:
                        conn.close()
                    st.success("Project updated.")
                    st.rerun()

    st.divider()

    # Milestones
    st.markdown("### Milestones")
    conn = connect()
    try:
        milestones = project_service.list_milestones(conn, project_id)
    finally:
        conn.close()

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
                conn = connect()
                try:
                    project_service.create_milestone(
                        conn,
                        MilestoneCreate(
                            project_id=project_id,
                            title=m_title.strip(),
                            due_date=due,
                            status=m_status,
                        ),
                    )
                finally:
                    conn.close()
                st.success("Milestone added.")
                st.rerun()

    for ms in milestones:
        line = f"• {ms.title}"
        if ms.due_date:
            line += f" (due {ms.due_date})"
        line += f" · {ms.status}"
        st.write(line)

    st.divider()

    # Linked tasks
    st.markdown("### Linked tasks")
    conn = connect()
    try:
        tasks = task_service.list_tasks(conn, project_id=project_id)
    finally:
        conn.close()

    if not tasks:
        st.info("No tasks linked to this project.")
    else:
        for t in tasks:
            done = t.status == "done"
            checked = st.checkbox(
                f"**{t.title}**", value=done, key=f"proj_task_done_{t.id}"
            )
            if checked != done:
                new_status = "done" if checked else "todo"
                conn = connect()
                try:
                    task_service.update_task(
                        conn, t.id, TaskUpdate(status=new_status)
                    )
                finally:
                    conn.close()
                st.rerun()
            st.caption(
                f"Status: {t.status} · Priority: {t.priority} · {t.estimated_minutes} min"
            )

    st.divider()

    # Add task to project
    with st.expander("Add a task to this project", expanded=False):
        with st.form(f"add_task_form_{project_id}", clear_on_submit=True):
            t_title = st.text_input("Task title", max_chars=200)
            t_desc = st.text_area("Description", max_chars=4000)
            col1, col2, col3 = st.columns(3)
            t_priority = col1.selectbox(
                "Priority", ["low", "medium", "high", "critical"], index=1
            )
            t_est = col2.number_input(
                "Estimated minutes", min_value=0, value=0, step=5
            )
            t_due = col3.date_input("Due date", value=None)
            t_status = st.selectbox(
                "Status", ["todo", "in_progress", "done", "cancelled"], index=0
            )
            t_added = st.form_submit_button("Add task")
            if t_added:
                if not t_title.strip():
                    st.error("Title is required.")
                else:
                    due = t_due.isoformat() if t_due else None
                    conn = connect()
                    try:
                        task_service.create_task(
                            conn,
                            TaskCreate(
                                title=t_title.strip(),
                                description=t_desc,
                                priority=t_priority,
                                estimated_minutes=int(t_est),
                                due_date=due,
                                status=t_status,
                                project_id=project_id,
                            ),
                        )
                    finally:
                        conn.close()
                    st.success("Task added.")
                    st.rerun()

    st.divider()

    # Notes
    st.markdown("### Notes")
    conn = connect()
    try:
        notes = project_service.list_notes(conn, project_id)
    finally:
        conn.close()

    with st.form(f"add_note_form_{project_id}", clear_on_submit=True):
        n_content = st.text_area("New note", max_chars=4000)
        n_added = st.form_submit_button("Add note")
        if n_added:
            if not n_content.strip():
                st.error("Content is required.")
            else:
                conn = connect()
                try:
                    project_service.create_note(
                        conn,
                        NoteCreate(project_id=project_id, content=n_content.strip()),
                    )
                finally:
                    conn.close()
                st.success("Note added.")
                st.rerun()

    for n in notes:
        st.write(f"• {n.content}")
        st.caption(n.created_at[:16])

    st.divider()
    if st.button("← Back to Projects"):
        st.query_params.clear()
        st.rerun()


def render_project_card(conn, project) -> None:
    """Render a clickable project card on the projects listing page."""
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{project.title}**")
        c2.caption(f"Status: {project.status}")
        c3.caption(f"Updated: {project.updated_at[:10]}")
        if project.description:
            st.caption(project.description)

        b1, b2 = st.columns([1, 1])
        if b1.button("View", key=f"view_proj_{project.id}"):
            st.query_params["project_id"] = str(project.id)
            st.rerun()
        if b2.button("Delete", key=f"del_proj_{project.id}", type="secondary"):
            conn = connect()
            try:
                project_service.delete_project(conn, project.id)
            finally:
                conn.close()
                st.success("Project deleted.")
                st.rerun()

