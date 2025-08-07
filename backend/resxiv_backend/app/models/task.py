"""
Task Pydantic Models

Contains request/response schemas for task management endpoints.
Mirrors the database models defined in `app.schemas.task` but removes
all persistence concerns.  These models are used exclusively for FastAPI
validation and serialization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# ENUMS (must stay in sync with DB enums)
# ---------------------------------------------------------------------


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ---------------------------------------------------------------------
# TASK LIST MODELS
# ---------------------------------------------------------------------


class TaskListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    position: Optional[int] = Field(None, ge=0)


class TaskListCreate(TaskListBase):
    """Payload for creating a new task list."""

    pass


class TaskListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    position: Optional[int] = Field(None, ge=0)


class TaskListResponse(TaskListBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# TASK MODELS
# ---------------------------------------------------------------------


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    status: TaskStatus = Field(TaskStatus.TODO)
    priority: TaskPriority = Field(TaskPriority.MEDIUM)
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, ge=0)
    actual_hours: Optional[int] = Field(None, ge=0)
    progress: Optional[int] = Field(0, ge=0, le=100)
    position: Optional[int] = Field(0, ge=0)
    is_milestone: Optional[bool] = False
    assigned_to: Optional[uuid.UUID] = None
    task_list_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None


class TaskCreate(TaskBase):
    """Payload for creating a task."""

    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    estimated_hours: Optional[int] = Field(None, ge=0)
    actual_hours: Optional[int] = Field(None, ge=0)
    progress: Optional[int] = Field(None, ge=0, le=100)
    position: Optional[int] = Field(None, ge=0)
    is_milestone: Optional[bool] = None
    assigned_to: Optional[uuid.UUID] = None
    task_list_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None


class TaskResponse(TaskBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListWithTasks(TaskListResponse):
    tasks: List[TaskResponse] = []


class TaskListCollectionResponse(BaseModel):
    lists: List[TaskListWithTasks]
    total: int


class TaskCollectionResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int 