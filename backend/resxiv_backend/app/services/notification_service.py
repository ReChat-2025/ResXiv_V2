from __future__ import annotations

"""Notification helpers (production-grade, minimal bloat).

Right now only project-invitation e-mails are required by the member-management
flows.  This module centralises lookup + e-mail dispatch so core services don’t
need to know whether they received an e-mail address or just a user-id.
"""

import uuid
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import EmailService
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

__all__ = ["send_project_invitation_notification"]


async def _resolve_email(
    session: AsyncSession, *, user_id: Optional[uuid.UUID], email: Optional[str]
) -> str:
    """Return a valid e-mail address, fetching the user if necessary."""
    if email:
        return email
    if not user_id:
        raise ValueError("Either email or user_id must be provided")
    user_repo = UserRepository(session)
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found – cannot send invitation")
    return user.email


async def send_project_invitation_notification(
    session: AsyncSession,
    *,
    inviter_name: str,
    project_name: str,
    invitation_token: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    email: Optional[str] = None,
) -> bool:
    """Send a project invitation/notification e-mail.

    `invitation_token` may be omitted when the user is already a project
    member; in that case we still inform them but without an accept-link.
    """
    try:
        to_email = await _resolve_email(session, user_id=user_id, email=email)
        email_service = EmailService()
        return await email_service.send_project_invitation(
            to_email=to_email,
            inviter_name=inviter_name,
            project_name=project_name,
            invitation_token=invitation_token or "",
        )
    except Exception as exc:
        logger.error("Failed to dispatch invitation email – %s", exc, exc_info=True)
        return False 