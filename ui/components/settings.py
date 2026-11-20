"""Settings page."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import time

import streamlit as st

from athena.config import AI_API_KEY, AI_PROVIDER, DATA_DIR, DB_PATH
from athena.database import connect
from athena.domain import setting_service


def _save_api_key_to_env(api_key: str) -> None:
    """Save the API key to a local .env file (never in source control)."""
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    existing = ""
    if env_file.exists():
        existing = env_file.read_text(encoding="utf-8")
    # Preserve existing content but add/override the API key line
    lines = existing.splitlines(keepends=True) if existing else []
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("ATHENA_AI_API_KEY="):
            new_lines.append("ATHENA_AI_API_KEY=" + api_key + "\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append("ATHENA_AI_API_KEY=" + api_key + "\n")
    env_file.write_text("".join(new_lines), encoding="utf-8")


def settings_page() -> None:
    st.subheader("Settings")
    st.caption("Configuration and environment. Secrets are never displayed or logged.")
    st.divider()

    st.markdown("### Database")
    st.write(f"Path: `{DB_PATH}`")
    st.write(f"Data directory: `{DATA_DIR}`")

    st.divider()

    st.markdown("### Planner availability")
    st.caption(
        "Configure your work day for the schedule planner. These values are "
        "saved to your local database and used when building schedules."
    )

    conn = connect()
    try:
        current = setting_service.get_availability(conn)
    finally:
        conn.close()

    col1, col2 = st.columns(2)
    work_start = col1.time_input(
        "Work day starts", value=current.work_start, key="avail_work_start"
    )
    work_end = col2.time_input(
        "Work day ends", value=current.work_end, key="avail_work_end"
    )

    col3, col4 = st.columns(2)
    lunch_start = col3.time_input(
        "Lunch starts",
        value=current.lunch_start or time(12, 0),
        key="avail_lunch_start",
    )
    lunch_end = col4.time_input(
        "Lunch ends",
        value=current.lunch_end or time(13, 0),
        key="avail_lunch_end",
    )

    col5, col6 = st.columns(2)
    break_every = col5.number_input(
        "Break every (minutes)",
        min_value=0,
        value=current.break_every_minutes,
        step=15,
        key="avail_break_every",
    )
    break_duration = col6.number_input(
        "Break duration (minutes)",
        min_value=0,
        value=current.break_duration_minutes,
        step=5,
        key="avail_break_duration",
    )

    if st.button("Save availability", type="primary", key="avail_save"):
        new_settings = setting_service.AvailabilitySettings(
            work_start=work_start,
            work_end=work_end,
            lunch_start=lunch_start,
            lunch_end=lunch_end,
            break_every_minutes=int(break_every),
            break_duration_minutes=int(break_duration),
        )
        conn = connect()
        try:
            setting_service.save_availability(conn, new_settings)
            conn.commit()
        finally:
            conn.close()
        st.success("Availability saved.")
        st.rerun()

    st.divider()

    st.markdown("### AI provider")
    st.caption(
        "Configure the AI provider for the chat interface. The API key is "
        "stored in a local `.env` file and is never displayed or logged."
    )
    col1, col2 = st.columns([3, 1])
    with col1:
        api_key = st.text_input(
            "AI API key",
            type="password",
            help="Your AI provider API key (e.g., OpenAI, Anthropic, etc.)",
            key="ai_api_key",
        )
    with col2:
        if st.button("Save API key", type="primary", key="ai_api_key_save"):
            if not api_key.strip():
                st.error("API key is required.")
            else:
                _save_api_key_to_env(api_key.strip())
                st.success("API key saved to `.env` file.")
                st.rerun()

    st.info(
        "Athena v0.1 runs without an AI provider. No model calls are made for "
        "deterministic features. Set `ATHENA_AI_PROVIDER` and `ATHENA_AI_API_KEY` "
        "in your environment to enable a real provider (see README)."
    )

    st.divider()

    st.markdown("### Security & privacy")
    st.markdown(
        "- All data is stored locally in SQLite by default.\n"
        "- No passwords, tokens, or private keys are stored in conversational memory.\n"
        "- API credentials must be provided via environment variables only.\n"
        "- Model-generated text is never executed as code.\n"
        "- Memories can be reviewed, edited, deleted, and exported at any time."
    )
