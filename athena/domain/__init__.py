"""Domain services for Athena.

Business logic lives here, independent of the Streamlit UI and the database
layer.  Services receive an open SQLite connection (from :func:`athena.database.connect`)
so callers can group multiple operations into a single transaction.
"""
