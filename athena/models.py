"""Pydantic domain models for Athena.

These models validate data coming into and going out of the database.  They
contain no persistence logic — that lives in ``athena.database`` and the
domain services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: str = Field(default="medium")
    estimated_minutes: int = Field(default=0, ge=0)
    due_date: Optional[str] = Field(default=None)  # ISO date YYYY-MM-DD
    status: str = Field(default="todo")
    project_id: Optional[int] = Field(default=None)

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {sorted(allowed)}")
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"todo", "in_progress", "done", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v

    @field_validator("due_date")
    @classmethod
    def _validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("due_date must be a YYYY-MM-DD date") from exc
        return v


# ---------------------------------------------------------------------------
# Fixed commitments (schedule planner input)
# ---------------------------------------------------------------------------

class FixedCommitment(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    start_dt: str  # ISO datetime
    end_dt: str    # ISO datetime
    source: Optional[str] = None

    @field_validator("start_dt", "end_dt")
    @classmethod
    def _validate_dt(cls, v: str) -> str:
        datetime.fromisoformat(v)
        return v

    @model_validator(mode="after")
    def _end_after_start(cls, v: "FixedCommitment") -> "FixedCommitment":
        if datetime.fromisoformat(v.end_dt) <= datetime.fromisoformat(v.start_dt):
            raise ValueError("end_dt must be after start_dt")
        return v

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Memories
# ---------------------------------------------------------------------------

class MemoryBase(BaseModel):
    kind: str = Field(default="knowledge_note")
    content: str = Field(..., min_length=1)
    source: Optional[str] = Field(default=None, max_length=500)
    approved: bool = Field(default=False)

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, v: str) -> str:
        allowed = {"profile_fact", "goal", "event", "knowledge_note"}
        if v not in allowed:
            raise ValueError(f"kind must be one of {sorted(allowed)}")
        return v


class Memory(MemoryBase):
    id: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    kind: Optional[str] = None
    content: Optional[str] = Field(default=None, min_length=1)
    source: Optional[str] = None
    approved: Optional[bool] = None

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"profile_fact", "goal", "event", "knowledge_note"}
        if v not in allowed:
            raise ValueError(f"kind must be one of {sorted(allowed)}")
        return v

class Task(TaskBase):
    id: int
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    due_date: Optional[str] = None
    status: Optional[str] = None
    project_id: Optional[int] = None

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"priority must be one of {sorted(allowed)}")
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"todo", "in_progress", "done", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v

    @field_validator("due_date")
    @classmethod
    def _validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("due_date must be a YYYY-MM-DD date") from exc
        return v


# ---------------------------------------------------------------------------
# Projects, milestones, notes
# ---------------------------------------------------------------------------

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    status: str = Field(default="active")

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"planning", "active", "on_hold", "completed", "archived"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v


class Project(ProjectBase):
    id: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None


class MilestoneBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_date: Optional[str] = Field(default=None)
    status: str = Field(default="upcoming")

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"upcoming", "in_progress", "done", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v

    @field_validator("due_date")
    @classmethod
    def _validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("due_date must be a YYYY-MM-DD date") from exc
        return v


class Milestone(MilestoneBase):
    id: int
    project_id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class MilestoneCreate(MilestoneBase):
    project_id: int


class NoteBase(BaseModel):
    content: str = Field(..., min_length=1)


class Note(NoteBase):
    id: int
    project_id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class NoteCreate(NoteBase):
    project_id: int


# ---------------------------------------------------------------------------
# Schedule planner output
# ---------------------------------------------------------------------------

class ScheduledBlock(BaseModel):
    """A single block produced by the scheduler."""

    start: str   # ISO datetime
    end: str     # ISO datetime
    title: str
    kind: str  # "task", "break", "commitment"
    task_id: Optional[int] = None
    commitment_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleResult(BaseModel):
    blocks: list[ScheduledBlock] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    unscheduled: list[int] = Field(default_factory=list)  # task ids that could not be placed

    model_config = ConfigDict(from_attributes=True)
