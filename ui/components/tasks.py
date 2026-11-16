"""Task manager page."""

from __future__ import annotations

from datetime import date

import streamlit as st

from athena.database import connect
from athena.domain import task_service
from athena.models import TaskCreate, TaskUpdate


def tasks_page() -> None:
    st.subheader("Task Manager")
    st.caption(
        "Create, edit, and track tasks. All changes are saved to the local SQLite database."
    )
    st.divider()

    # ---- Add new task -------------------------------------------------
    with st.expander("Add a new task", expanded=False):
        with st.form("add_task_form", clear_on_submit=True):
            title = st.text_input("Title *", max_chars=200)
            description = st.text_area("Description", max_chars=4000)
            col1, col2, col3 = st.columns(3)
            priority = col1.selectbox(
                "Priority", ["low", "medium", "high", "critical"], index=1
            )
            estimated = col2.number_input("Estimated minutes", min_value=0, value=0, step=5)
            due_date = col3.date_input("Due date", value=None)
            status = st.selectbox(
                "Status", ["todo", "in_progress", "done", "cancelled"], index=0
            )
            submitted = st.form_submit_button("Create task")
            if submitted:
                if not title.strip():
                    st.error("Title is required.")
                else:
                    due = due_date.isoformat() if due_date else None
                    conn = connect()
                    try:
                        task_service.create_task(
                            conn,
                            TaskCreate(
                                title=title.strip(),
                                description=description,
                                priority=priority,
                                estimated_minutes=int(estimated),
                                due_date=due,
                                status=status,
                            ),
                        )
                        st.success("Task created.")
                    finally:
                        conn.close()
                    st.rerun()

    st.divider()

    # ---- Filters -------------------------------------------------------
    st.markdown("### Tasks")
    colf1, colf2 = st.columns([2, 2])
    filter_status = colf1.selectbox(
        "Filter by status",
        ["All", "todo", "in_progress", "done", "cancelled", "overdue"],
        index=0,
    )
    filter_project = colf2.text_input("Filter by project (title contains)", value="")

    conn = connect()
    try:
        if filter_status == "overdue":
            tasks = task_service.get_overdue_tasks(conn)
        elif filter_status == "All":
            tasks = task_service.list_tasks(conn)
        else:
            tasks = task_service.list_tasks(conn, status=filter_status)
        if filter_project.strip():
            tasks = [
                t
                for t in tasks
                if filter_project.lower() in (t.title or "").lower()
            ]
    finally:
        conn.close()

    if not tasks:
        st.info("No tasks found. Use the form above to create your first task.")
        return

    # ---- Task rows -----------------------------------------------------
    for t in tasks:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            done = t.status == "done"
            checked = c1.checkbox(
                f"**{t.title}**", value=done, key=f"task_done_{t.id}"
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

            c2.caption(f"Status: {t.status}")
            c3.caption(f"Priority: {t.priority}")
            c4.caption(f"Due: {t.due_date or '\u2014'}")

            meta = []
            if t.description:
                meta.append(f"Description: {t.description}")
            meta.append(f"Estimated: {t.estimated_minutes} min")
            if t.created_at:
                meta.append(f"Created: {t.created_at[:10]}")
            if t.completed_at:
                meta.append(f"Completed: {t.completed_at[:16]}")
            st.caption(" \u00b7 ".join(meta))

            # Edit / delete controls
            e1, e2, _ = st.columns([1, 1, 6])
            if e1.button("Edit", key=f"edit_{t.id}"):
                st.session_state[f"editing_{t.id}"] = True
            if e2.button("Delete", key=f"del_{t.id}", type="secondary"):
                conn = connect()
                try:
                    task_service.delete_task(conn, t.id)
                finally:
                    conn.close()
                st.success("Task deleted.")
                st.rerun()

            if st.session_state.get(f"editing_{t.id}"):
                _render_edit_form(t)


def _render_edit_form(t) -> None:
    with st.form(f"edit_form_{t.id}"):
        st.markdown(f"#### Edit: {t.title}")
        title = st.text_input("Title", value=t.title, max_chars=200)
        description = st.text_area("Description", value=t.description, max_chars=4000)
        col1, col2, col3 = st.columns(3)
        priority = col1.selectbox(
            "Priority",
            ["low", "medium", "high", "critical"],
            index=["low", "medium", "high", "critical"].index(t.priority),
        )
        estimated = col2.number_input(
            "Estimated minutes",
            min_value=0,
            value=int(t.estimated_minutes or 0),
            step=5,
        )
        due_val = None
        if t.due_date:
            try:
                due_val = date.fromisoformat(t.due_date)
            except ValueError:
                due_val = None
        due_date = col3.date_input("Due date", value=due_val)
        status = st.selectbox(
            "Status",
            ["todo", "in_progress", "done", "cancelled"],
            index=["todo", "in_progress", "done", "cancelled"].index(t.status),
        )
        col_save, col_cancel = st.columns([1, 1])
        save = col_save.form_submit_button("Save changes")
        cancel = col_cancel.form_submit_button("Cancel")
        if cancel:
            st.session_state[f"editing_{t.id}"] = False
            st.rerun()
        if save:
            if not title.strip():
                st.error("Title is required.")
                return
            due = due_date.isoformat() if due_date else None
            updates = TaskUpdate(
                title=title.strip(),
                description=description,
                priority=priority,
                estimated_minutes=int(estimated),
                due_date=due,
                status=status,
            )
            conn = connect()
            try:
                task_service.update_task(conn, t.id, updates)
            finally:
                conn.close()
            st.session_state[f"editing_{t.id}"] = False
            st.success("Task updated.")
            st.rerun()
