"""
Project Analytics Endpoints - L6 Engineering Standards

Focused module for project-specific analytics functionality.
Extracted from bloated analytics.py for SOLID compliance.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.core.error_handling import handle_service_errors, ErrorCodes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/project/{project_id}/analytics", response_model=Dict[str, Any])
@handle_service_errors("project analytics retrieval")
async def get_project_analytics(
    project_id: str,
    date_from: Optional[date] = Query(None, description="Start date for analytics"),
    date_to: Optional[date] = Query(None, description="End date for analytics"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get comprehensive analytics for a specific project"""
    # Set default date range
    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    # Get project basic info
    project_result = await session.execute(
        text("""
            SELECT p.name, p.description, p.created_at,
                   COUNT(DISTINCT pm.user_id) as member_count,
                   COUNT(DISTINCT pp.paper_id) as paper_count
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            LEFT JOIN project_papers pp ON p.id = pp.project_id
            WHERE p.id = :project_id AND p.deleted_at IS NULL
            GROUP BY p.id, p.name, p.description, p.created_at
        """),
        {"project_id": project_id}
    )
    
    project_row = project_result.fetchone()
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get member activity over time (PostgreSQL-based data only)
    activity_result = await session.execute(
        text("""
            SELECT DATE(pm.added_at) as activity_date,
                   COUNT(DISTINCT pm.user_id) as active_members,
                   0 as message_count
            FROM project_members pm
            JOIN projects p ON pm.project_id = p.id
            WHERE p.id = :project_id 
                AND pm.added_at BETWEEN :date_from AND :date_to
            GROUP BY DATE(pm.added_at)
            ORDER BY activity_date DESC
        """),
        {"project_id": project_id, "date_from": date_from, "date_to": date_to}
    )
    
    activity_data = []
    for row in activity_result.fetchall():
        activity_data.append({
            "date": row.activity_date.isoformat(),
            "active_members": row.active_members,
            "message_count": 0  # Messages are in MongoDB, not accessible from PostgreSQL
        })
    
    # Get collaboration metrics (PostgreSQL data only)
    collaboration_result = await session.execute(
        text("""
            SELECT 
                COUNT(DISTINCT c.id) as conversation_count,
                0 as total_messages,
                COUNT(DISTINCT t.id) as task_count,
                COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks
            FROM projects p
            LEFT JOIN conversations c ON p.id = c.entity AND c.type = 'GROUP'
            LEFT JOIN tasks t ON p.id = t.project_id
            WHERE p.id = :project_id
        """),
        {"project_id": project_id}
    )
    
    collab_row = collaboration_result.fetchone()
    
    return {
        "success": True,
        "project_info": {
            "name": project_row.name,
            "description": project_row.description,
            "created_at": project_row.created_at.isoformat(),
            "member_count": project_row.member_count or 0,
            "paper_count": project_row.paper_count or 0
        },
        "date_range": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "activity_timeline": activity_data,
        "collaboration_metrics": {
            "conversation_count": collab_row.conversation_count or 0,
            "total_messages": collab_row.total_messages or 0,
            "task_count": collab_row.task_count or 0,
            "completed_tasks": collab_row.completed_tasks or 0,
            "task_completion_rate": round(
                (collab_row.completed_tasks or 0) / max(collab_row.task_count or 1, 1) * 100, 1
            )
        }
    }


@router.get("/project/{project_id}/collaboration", response_model=Dict[str, Any])
@handle_service_errors("project collaboration analytics")
async def get_project_collaboration_analytics(
    project_id: str,
    days: int = Query(30, ge=1, le=90, description="Days to analyze"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get detailed collaboration analytics for a project"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get member collaboration patterns
    collaboration_result = await session.execute(
        text("""
            SELECT 
                u.username,
                COUNT(DISTINCT m.conversation_id) as conversations_participated,
                COUNT(m.id) as messages_sent,
                COUNT(DISTINCT t.id) as tasks_created,
                COUNT(DISTINCT ta.task_id) as tasks_assigned
            FROM project_members pm
            JOIN users u ON pm.user_id = u.id
            LEFT JOIN messages m ON u.id = m.user_id 
                AND m.created_at >= :start_date
            LEFT JOIN conversations c ON m.conversation_id = c.id 
                AND c.project_id = :project_id
            LEFT JOIN tasks t ON u.id = t.created_by 
                AND t.project_id = :project_id
                AND t.created_at >= :start_date
            LEFT JOIN task_assignments ta ON u.id = ta.user_id
            LEFT JOIN tasks t2 ON ta.task_id = t2.id 
                AND t2.project_id = :project_id
            WHERE pm.project_id = :project_id
            GROUP BY u.id, u.username
            ORDER BY messages_sent DESC
        """),
        {"start_date": start_date, "project_id": project_id}
    )
    
    member_analytics = []
    for row in collaboration_result.fetchall():
        member_analytics.append({
            "username": row.username,
            "conversations_participated": row.conversations_participated or 0,
            "messages_sent": row.messages_sent or 0,
            "tasks_created": row.tasks_created or 0,
            "tasks_assigned": row.tasks_assigned or 0
        })
    
    return {
        "success": True,
        "project_id": project_id,
        "period_days": days,
        "member_analytics": member_analytics,
        "summary": {
            "total_members": len(member_analytics),
            "active_members": len([m for m in member_analytics if m["messages_sent"] > 0]),
            "avg_messages_per_member": round(
                sum(m["messages_sent"] for m in member_analytics) / max(len(member_analytics), 1), 1
            )
        }
    } 