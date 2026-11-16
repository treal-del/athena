"""Settings page."""

from __future__ import annotations

import os

import streamlit as st

from athena.config import AI_API_KEY, AI_PROVIDER, DATA_DIR, DB_PATH


def settings_page() -> None:
    st.subheader("Settings")
    st.caption("Configuration and environment. Secrets are never displayed or logged.")
    st.divider()

    st.markdown("### Database")
    st.write(f"Path: `{DB_PATH}`")
    st.write(f"Data directory: `{DATA_DIR}`")

    st.divider()

    st.markdown("### AI provider")
    st.write(f"Configured provider: `{AI_PROVIDER or '(none — deterministic mode)'}`")
    st.write(
        "API key present: "
        + ("yes" if AI_API_KEY else "no")
        + "  (value is never displayed or logged)"
    )
    st.info(
        "Athena v0.1 runs without an AI provider. No model calls are made for "
        "deterministic features, and Athena never fakes intelligence. To add a "
        "provider, set ATHENA_AI_PROVIDER and ATHENA_AI_API_KEY in your "
        "environment and implement an athena.ai.AIProvider subclass."
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
