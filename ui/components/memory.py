"""Memory manager page.

Supports profile facts, goals, events, and knowledge notes.  Memories are
unapproved by default and must be explicitly approved before they are used
in reports.  Users can search, edit, approve, and delete memories.
"""

from __future__ import annotations

import streamlit as st

from athena.database import connect
from athena.domain import memory_service
from athena.models import MemoryCreate, MemoryUpdate
from athena.memory import search_with_source


def memory_page() -> None:
    st.subheader("Memory Manager")
    st.caption(
        "Remember approved information: profile facts, goals, events, and "
        "knowledge notes. Memories are unapproved by default."
    )
    st.divider()

    # ---- Add memory ----------------------------------------------------
    with st.expander("Save a new memory", expanded=False):
        with st.form("add_memory_form", clear_on_submit=True):
            kind = st.selectbox(
                "Kind", ["profile_fact", "goal", "event", "knowledge_note"], index=3
            )
            content = st.text_area("Content *", max_chars=4000)
            source = st.text_input("Source (where did this come from?)", max_chars=500)
            approve_now = st.checkbox("Approve immediately", value=False)
            m_submitted = st.form_submit_button("Save memory")
            if m_submitted:
                if not content.strip():
                    st.error("Content is required.")
                else:
                    conn = connect()
                    try:
                        memory_service.create_memory(
                            conn,
                            MemoryCreate(
                                kind=kind,
                                content=content.strip(),
                                source=source.strip() or None,
                                approved=approve_now,
                            ),
                        )
                    finally:
                        conn.close()
                    st.success("Memory saved.")
                    st.rerun()

    st.divider()

    # ---- Search / list -------------------------------------------------
    st.markdown("### Search memories")
    col1, col2 = st.columns([3, 1])
    query = col1.text_input("Search keyword (content or source)", value="")
    kind_filter = col2.selectbox(
        "Filter by kind",
        ["All", "profile_fact", "goal", "event", "knowledge_note"],
        index=0,
    )
    approved_only = st.checkbox("Approved only", value=False)

    conn = connect()
    try:
        if query.strip():
            memories = list(
                search_with_source(
                    conn,
                    query,
                    kind=None if kind_filter == "All" else kind_filter,
                    approved_only=approved_only,
                )
            )
        else:
            memories = memory_service.list_memories(
                conn,
                kind=None if kind_filter == "All" else kind_filter,
                approved=approved_only if approved_only else None,
            )
    finally:
        conn.close()

    if not memories:
        st.info("No memories found. Save your first memory above.")
        return

    st.markdown(f"**{len(memories)} memory(ies)**")

    # ---- Memory rows ---------------------------------------------------
    for m in memories:
        with st.container(border=True):
            approved = bool(m.approved)
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{m.kind}**")
            c2.caption(f"Approved: {'yes' if approved else 'no'}")
            c3.caption(m.created_at[:16])
            st.write(m.content)
            if m.source:
                st.caption(
                    f"Source: {m.source} \u00b7 Created: {m.created_at[:10]}"
                )

            e1, e2, e3, _ = st.columns([1, 1, 1, 6])
            if not approved:
                if e1.button("Approve", key=f"approve_{m.id}"):
                    conn = connect()
                    try:
                        memory_service.approve_memory(conn, m.id, True)
                    finally:
                        conn.close()
                    st.success("Memory approved.")
                    st.rerun()
            else:
                if e1.button("Unapprove", key=f"unapprove_{m.id}"):
                    conn = connect()
                    try:
                        memory_service.approve_memory(conn, m.id, False)
                    finally:
                        conn.close()
                    st.success("Memory unapproved.")
                    st.rerun()

            if e2.button("Edit", key=f"edit_mem_{m.id}"):
                st.session_state[f"editing_mem_{m.id}"] = True
            if e3.button("Delete", key=f"del_mem_{m.id}", type="secondary"):
                conn = connect()
                try:
                    memory_service.delete_memory(conn, m.id)
                finally:
                    conn.close()
                    st.success("Memory deleted.")
                    st.rerun()

            if st.session_state.get(f"editing_mem_{m.id}"):
                _render_edit_form(m)


def _render_edit_form(m) -> None:
    with st.form(f"edit_mem_form_{m.id}"):
        st.markdown(f"#### Edit memory ({m.id})")
        kind = st.selectbox(
            "Kind",
            ["profile_fact", "goal", "event", "knowledge_note"],
            index=["profile_fact", "goal", "event", "knowledge_note"].index(m.kind),
        )
        content = st.text_area("Content", value=m.content, max_chars=4000)
        source = st.text_input("Source", value=m.source or "", max_chars=500)
        approved = st.checkbox("Approved", value=bool(m.approved))
        col_save, col_cancel = st.columns([1, 1])
        save = col_save.form_submit_button("Save changes")
        cancel = col_cancel.form_submit_button("Cancel")
        if cancel:
            st.session_state[f"editing_mem_{m.id}"] = False
            st.rerun()
        if save:
            if not content.strip():
                st.error("Content is required.")
                return
            conn = connect()
            try:
                memory_service.update_memory(
                    conn,
                    m.id,
                    MemoryUpdate(
                        kind=kind,
                        content=content.strip(),
                        source=source.strip() or None,
                        approved=approved,
                    ),
                )
            finally:
                conn.close()
            st.session_state[f"editing_mem_{m.id}"] = False
            st.success("Memory updated.")
            st.rerun()
