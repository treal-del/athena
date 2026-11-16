"""Export / Backup page."""

from __future__ import annotations

import streamlit as st

from athena.config import DB_PATH, BACKUP_DIR, DATA_DIR
from athena.export import backup_database, export_json, export_archive


def export_page() -> None:
    st.subheader("Export / Backup")
    st.caption(
        "All Athena data lives in a local SQLite database. Back it up or "
        "export it to JSON/zip at any time. No secrets are stored in the DB."
    )
    st.divider()

    st.write(f"Database file: `{DB_PATH}`")
    st.write(f"Backup directory: `{BACKUP_DIR}`")

    st.divider()

    st.markdown("### Create backup")
    st.write("Download a copy of the live SQLite database.")
    if st.button("Create & download database backup", type="primary"):
        try:
            out = backup_database()
            data = out.read_bytes()
            st.download_button(
                label="Download backup",
                data=data,
                file_name=out.name,
                mime="application/octet-stream",
            )
            st.success(f"Backup created at {out}")
        except Exception as exc:  # noqa: BLE001 - surface to user
            st.error(f"Backup failed: {exc}")

    st.divider()

    st.markdown("### Export to JSON")
    st.write("Dump every table to a single JSON file.")
    if st.button("Create & download JSON export"):
        try:
            out = BACKUP_DIR / "athena_export.json"
            export_json(out)
            data = out.read_bytes()
            st.download_button(
                label="Download JSON export",
                data=data,
                file_name="athena_export.json",
                mime="application/json",
            )
            st.success("JSON export created.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Export failed: {exc}")

    st.divider()

    st.markdown("### Full archive (zip)")
    st.write("Zip archive containing the database and a JSON export.")
    if st.button("Create & download archive"):
        try:
            out = export_archive()
            data = out.read_bytes()
            st.download_button(
                label="Download archive",
                data=data,
                file_name=out.name,
                mime="application/zip",
            )
            st.success("Archive created.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Archive failed: {exc}")

    st.divider()

    st.markdown("### Data directory")
    st.write(f"`{DATA_DIR}`")
    st.caption(
        "You can back up this entire folder to preserve all Athena data. "
        "Change the location with the ATHENA_DATA_DIR environment variable."
    )
