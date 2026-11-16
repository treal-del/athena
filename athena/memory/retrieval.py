"""Memory retrieval helpers.

Builds on :mod:`athena.domain.memory_service` to return memories with their
timestamps and source information.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..domain.memory_service import Memory, search_memories


def search_with_source(
    conn,
    query: str,
    *,
    kind: Optional[str] = None,
    approved_only: bool = False,
    limit: int = 20,
) -> Sequence[Memory]:
    """Search memories and return them with source and timestamp information.

    Results come from :func:`athena.domain.memory_service.search_memories`
    which already returns each memory with ``content``, ``source``,
    ``created_at``, ``updated_at`` and ``approved``.  The service orders by
    creation date (newest first).

    Parameters
    ----------
    query:
        Keyword matched (case-insensitive) against memory content and source.
    kind:
        Optional memory kind filter (profile_fact, goal, event, knowledge_note).
    approved_only:
        When True, only approved memories are returned.
    limit:
        Maximum number of memories to return.
    """
    return list(
        search_memories(
            conn,
            query,
            kind=kind,
            approved_only=approved_only,
            limit=limit,
        )
    )


__all__ = ["search_with_source"]

