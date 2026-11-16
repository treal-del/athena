"""Tests for memory domain operations."""

from __future__ import annotations

from athena.domain import memory_service
from athena.models import MemoryCreate, MemoryUpdate


def _make(conn, **kwargs):
    data = dict(kind="knowledge_note", content="Hello world", source="test")
    data.update(kwargs)
    return memory_service.create_memory(conn, MemoryCreate(**data))


def test_create_and_get_memory(conn):
    m = _make(conn, kind="goal", content="Run a marathon", source="user")
    assert m.id is not None
    assert m.approved is False
    fetched = memory_service.get_memory(conn, m.id)
    assert fetched is not None
    assert fetched.content == "Run a marathon"


def test_get_memory_missing(conn):
    assert memory_service.get_memory(conn, 99999) is None


def test_list_and_search(conn):
    _make(conn, kind="profile_fact", content="I like tea", source="profile")
    _make(conn, kind="goal", content="Learn Python", source="user")
    _make(conn, kind="knowledge_note", content="Tea is brewed hot", source="web")

    all_memories = memory_service.list_memories(conn)
    assert len(all_memories) == 3

    found = memory_service.search_memories(conn, "tea")
    assert len(found) == 2  # content "I like tea" and "Tea is brewed hot"
    for m in found:
        assert "tea" in m.content.lower() or "tea" in (m.source or "").lower()

    goals = memory_service.list_memories(conn, kind="goal")
    assert len(goals) == 1
    assert goals[0].content == "Learn Python"

    # Each memory carries timestamps and source.
    assert found[0].created_at
    assert found[0].updated_at


def test_approve_and_edit_and_delete(conn):
    m = _make(conn)
    assert m.approved is False

    approved = memory_service.approve_memory(conn, m.id, True)
    assert approved.approved is True

    unapproved = memory_service.approve_memory(conn, m.id, False)
    assert unapproved.approved is False

    updated = memory_service.update_memory(
        conn, m.id, MemoryUpdate(content="Updated content", approved=True)
    )
    assert updated.content == "Updated content"
    assert updated.approved is True

    assert memory_service.delete_memory(conn, m.id) is True
    assert memory_service.get_memory(conn, m.id) is None
    assert memory_service.delete_memory(conn, m.id) is False
