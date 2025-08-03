"""
Task Management SQLAlchemy Models

Defines database models that mirror the `tasks_*` tables detailed in
`db_details.txt`.

Only a subset of tables are included for the initial implementation
(TaskList, Task, TaskAssignee).  Additional tables such as
TaskDependency, TaskComment, TaskAttachment, etc. can be added later
without breaking existing code.

All models inherit from `Base` so that Alembic can detect them
automatically when generating migrations.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


# ---------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------


class TaskStatusEnum(str, enum.Enum):
    """Workflow states for a task."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriorityEnum(str, enum.Enum):
    """Priority levels for a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ---------------------------------------------------------------------
# CORE TABLES
# ---------------------------------------------------------------------


class TaskList(Base):
    """task_lists

    Logical container used to group tasks within a project (e.g. Backlog,
    In Progress, Done). Supports manual ordering via the `position`
    column so that UI clients can display lists in a custom order.
    """

    __tablename__ = "task_lists"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: str = Column(Text, nullable=False)
    description: str | None = Column(Text, nullable=True)
    color: str = Column(String, default="#3498db")
    position: int = Column(Integer, default=0)

    created_by: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships ----------------------------------------------------
    tasks = relationship(
        "Task",
        back_populates="task_list",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Task(Base):
    """tasks

    Represents an actionable item within a project. A task may optionally
    reference a parent task to implement sub-tasks.
    """

    __tablename__ = "tasks"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    task_list_id: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True
    )
    parent_task_id: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )

    title: str = Column(Text, nullable=False)
    description: str | None = Column(Text, nullable=True)

    status: str = Column(String, default=TaskStatusEnum.TODO.value)
    priority: str = Column(String, default=TaskPriorityEnum.MEDIUM.value)

    due_date = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)

    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)

    progress = Column(Integer, default=0)
    position = Column(Integer, default=0)
    is_milestone = Column(Boolean, default=False)

    created_by: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="valid_progress"),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'review', 'done', 'cancelled')",
            name="valid_task_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="valid_task_priority",
        ),
    )

    # Relationships ----------------------------------------------------
    task_list = relationship("TaskList", back_populates="tasks", lazy="joined")
    # Self-referential one-to-many so that a task can own many subtasks.
    # `subtasks` is the collection (one-to-many) side with delete-orphan
    # cascade; `parent_task` is the many-to-one side and **must not** have
    # delete-orphan to avoid the mapper error.
    parent_task = relationship(
        "Task", remote_side=[id], back_populates="subtasks"
    )
    subtasks = relationship(
        "Task",
        back_populates="parent_task",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
    )


class TaskAssignee(Base):
    """task_assignees

    Allows multiple users to be assigned to the same task.
    """

    __tablename__ = "task_assignees"

    task_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_by: uuid.UUID | None = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now()) 