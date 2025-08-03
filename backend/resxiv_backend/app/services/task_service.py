"""
Task Service
============
Encapsulates business rules for task management.  The service layer
coordinates validation, access-control checks and repository calls while
keeping API endpoints thin and reusable.

Responsibilities
----------------
• Ensure the current user is a member of the project before mutating data
• Provide simple dict/response objects for endpoints to serialise
• Keep transactions atomic – commit only after *all* operations succeed
• Leave DB-specific code to the repository layer so the service remains
  framework-agnostic and easy to unit-test
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.task_repository import TaskRepository
from app.repositories.project_repository import ProjectRepository
from app.models.task import (
    TaskListCreate,
    TaskListUpdate,
    TaskCreate,
    TaskUpdate,
    TaskListResponse,
    TaskResponse,
    TaskListCollectionResponse,
    TaskCollectionResponse,
)

logger = logging.getLogger(__name__)


class TaskService:
    """High-level operations for task management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TaskRepository(session)
        self.project_repo = ProjectRepository(session)

    # ------------------------------------------------------------------
    # Task-List operations
    # ------------------------------------------------------------------
    async def create_task_list(
        self, project_id: uuid.UUID, user_id: uuid.UUID, list_data: TaskListCreate
    ) -> Dict[str, Any]:
        if not await self.project_repo.is_user_member(project_id, user_id):
            return {"success": False, "error": "Access denied"}

        task_list = await self.repo.create_task_list(
            project_id=project_id, created_by=user_id, **list_data.model_dump()
        )
        await self.session.commit()
        return {
            "success": True,
            "list": TaskListResponse.model_validate(task_list),
        }

    async def get_project_task_lists(
        self, project_id: uuid.UUID
    ) -> TaskListCollectionResponse:
        lists = await self.repo.get_project_task_lists(project_id)
        response_lists = [
            TaskListResponse.model_validate(tl).dict() | {"tasks": []}
            for tl in lists
        ]
        return TaskListCollectionResponse(lists=response_lists, total=len(response_lists))

    async def update_task_list(
        self, list_id: uuid.UUID, user_id: uuid.UUID, update_data: TaskListUpdate
    ) -> Dict[str, Any]:
        task_list = await self.repo.get_task_list(list_id)
        if not task_list:
            return {"success": False, "error": "Task list not found"}

        if not await self.project_repo.is_user_member(task_list.project_id, user_id):
            return {"success": False, "error": "Access denied"}

        updated = await self.repo.update_task_list(
            list_id, **update_data.model_dump(exclude_none=True)
        )
        await self.session.commit()
        return {"success": True, "list": TaskListResponse.model_validate(updated)}

    async def delete_task_list(self, list_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        task_list = await self.repo.get_task_list(list_id)
        if not task_list:
            return {"success": False, "error": "Task list not found"}

        if not await self.project_repo.is_user_member(task_list.project_id, user_id):
            return {"success": False, "error": "Access denied"}

        rows = await self.repo.delete_task_list(list_id)
        await self.session.commit()
        return {"success": True, "deleted": rows > 0}

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------
    async def create_task(
        self, project_id: uuid.UUID, user_id: uuid.UUID, task_data: TaskCreate
    ) -> Dict[str, Any]:
        if not await self.project_repo.is_user_member(project_id, user_id):
            return {"success": False, "error": "Access denied"}

        task = await self.repo.create_task(
            project_id=project_id, created_by=user_id, **task_data.model_dump()
        )
        await self.session.commit()
        return {"success": True, "task": TaskResponse.model_validate(task)}

    async def get_project_tasks(
        self, project_id: uuid.UUID, page: int = 1, size: int = 50
    ) -> TaskCollectionResponse:
        offset = (page - 1) * size
        tasks, total = await self.repo.get_project_tasks(project_id, limit=size, offset=offset)
        return TaskCollectionResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
        )

    async def get_task(self, task_id: uuid.UUID) -> Optional[TaskResponse]:
        task = await self.repo.get_task(task_id)
        if not task:
            return None
        return TaskResponse.model_validate(task)

    async def update_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID, update_data: TaskUpdate
    ) -> Dict[str, Any]:
        task = await self.repo.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        if not await self.project_repo.is_user_member(task.project_id, user_id):
            return {"success": False, "error": "Access denied"}

        updated = await self.repo.update_task(
            task_id, **update_data.model_dump(exclude_none=True)
        )
        await self.session.commit()
        return {"success": True, "task": TaskResponse.model_validate(updated)}

    async def delete_task(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        task = await self.repo.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        if not await self.project_repo.is_user_member(task.project_id, user_id):
            return {"success": False, "error": "Access denied"}

        rows = await self.repo.delete_task(task_id)
        await self.session.commit()
        return {"success": True, "deleted": rows > 0} 