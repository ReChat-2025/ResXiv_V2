"""
Task Repository
===============
Low-level database helpers for task management.  All functions are
asynchronous to support SQLAlchemy’s async engine and are deliberately
kept free of business logic.

This layer can be unit-tested in isolation by passing in an `AsyncSession`
instance connected to an in-memory database.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select, update, delete, asc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.task import TaskList, Task  # SQLAlchemy models


class TaskRepository:
    """Data-access helper around *task_lists* and *tasks* tables."""

    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    # ------------------------------------------------------------------
    # Task-List helpers
    # ------------------------------------------------------------------
    async def create_task_list(
        self, project_id: uuid.UUID, created_by: uuid.UUID, **kwargs
    ) -> TaskList:
        """Insert a new *task_list* and return the persisted row."""
        task_list = TaskList(project_id=project_id, created_by=created_by, **kwargs)
        self._session.add(task_list)
        await self._session.flush()
        await self._session.refresh(task_list)
        return task_list

    async def get_task_list(self, list_id: uuid.UUID) -> Optional[TaskList]:
        stmt = select(TaskList).where(TaskList.id == list_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_task_lists(self, project_id: uuid.UUID) -> List[TaskList]:
        stmt = (
            select(TaskList)
            .where(TaskList.project_id == project_id)
            .order_by(asc(TaskList.position), asc(TaskList.created_at))
        )
        result = await self._session.scalars(stmt)
        return list(result)

    async def update_task_list(self, list_id: uuid.UUID, **update_data) -> Optional[TaskList]:
        if not update_data:
            return await self.get_task_list(list_id)
        stmt = (
            update(TaskList)
            .where(TaskList.id == list_id)
            .values(**update_data)
            .returning(TaskList)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_task_list(self, list_id: uuid.UUID) -> int:
        stmt = delete(TaskList).where(TaskList.id == list_id)
        result = await self._session.execute(stmt)
        return result.rowcount

    # ------------------------------------------------------------------
    # Task helpers
    # ------------------------------------------------------------------
    async def create_task(
        self, project_id: uuid.UUID, created_by: uuid.UUID, **kwargs
    ) -> Task:
        task = Task(project_id=project_id, created_by=created_by, **kwargs)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_tasks(
        self, project_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> Tuple[List[Task], int]:
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(asc(Task.position), asc(Task.created_at))
            .limit(limit)
            .offset(offset)
        )
        tasks_result = await self._session.scalars(stmt)
        tasks = list(tasks_result)

        count_stmt = select(func.count()).select_from(Task).where(Task.project_id == project_id)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        return tasks, total

    async def update_task(self, task_id: uuid.UUID, **update_data) -> Optional[Task]:
        if not update_data:
            return await self.get_task(task_id)
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(**update_data)
            .returning(Task)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_task(self, task_id: uuid.UUID) -> int:
        stmt = delete(Task).where(Task.id == task_id)
        result = await self._session.execute(stmt)
        return result.rowcount 