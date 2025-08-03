"""
User Analytics Endpoints - L6 Engineering Standards

Focused module for user-specific analytics functionality.
Extracted from bloated analytics.py for SOLID compliance.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.dependencies import get_postgres_session, get_current_user_required
from app.core.error_handling import handle_service_errors, ErrorCodes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/{user_id}/analytics", response_model=Dict[str, Any])
@handle_service_errors("user analytics retrieval")
async def get_user_analytics(
    user_id: str,
    date_from: Optional[date] = Query(None, description="Start date for analytics"),
    date_to: Optional[date] = Query(None, description="End date for analytics"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get comprehensive analytics for a specific user"""
    # Check permission (users can only see their own analytics)
    if current_user["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Can only view your own analytics"
        )
    
    # Set default date range
    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)
    
    # Get user basic info and activity metrics (PostgreSQL data only)
    user_result = await session.execute(
        text("""
            SELECT u.name, u.email, u.created_at,
                   COUNT(DISTINCT pm.project_id) as projects_joined,
                   COUNT(DISTINCT p.id) as papers_uploaded,
                   0 as messages_sent
            FROM users u
            LEFT JOIN project_members pm ON u.id = pm.user_id
            LEFT JOIN project_papers pp ON pm.project_id = pp.project_id
            LEFT JOIN papers p ON pp.paper_id = p.id 
                AND p.created_at BETWEEN :date_from AND :date_to
            WHERE u.id = :user_id AND u.deleted_at IS NULL
            GROUP BY u.id, u.name, u.email, u.created_at
        """),
        {"date_from": date_from, "date_to": date_to, "user_id": user_id}
    )
    
    user_row = user_result.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get activity timeline (PostgreSQL data only)
    activity_result = await session.execute(
        text("""
            SELECT DATE(pp.added_at) as activity_date,
                   COUNT(*) as activity_count,
                   'papers' as activity_type
            FROM project_papers pp 
            JOIN project_members pm ON pp.project_id = pm.project_id
            WHERE pm.user_id = :user_id AND pp.added_at BETWEEN :date_from AND :date_to
            GROUP BY DATE(pp.added_at)
            UNION ALL
            SELECT DATE(pm.added_at) as activity_date,
                   COUNT(*) as activity_count,
                   'projects_joined' as activity_type
            FROM project_members pm 
            WHERE pm.user_id = :user_id AND pm.added_at BETWEEN :date_from AND :date_to
            GROUP BY DATE(pm.added_at)
            ORDER BY activity_date DESC
        """),
        {"user_id": user_id, "date_from": date_from, "date_to": date_to}
    )
    
    activity_timeline = {}
    for row in activity_result.fetchall():
        date_str = row.activity_date.isoformat()
        if date_str not in activity_timeline:
            activity_timeline[date_str] = {}
        activity_timeline[date_str][row.activity_type] = row.activity_count
    
    return {
        "success": True,
        "user_info": {
            "username": user_row.username,
            "email": user_row.email,
            "member_since": user_row.created_at.isoformat(),
            "projects_joined": user_row.projects_joined or 0,
            "papers_uploaded": user_row.papers_uploaded or 0,
            "messages_sent": user_row.messages_sent or 0
        },
        "date_range": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "activity_timeline": activity_timeline
    }


@router.get("/user/engagement", response_model=Dict[str, Any])
@handle_service_errors("user engagement retrieval")
async def get_user_engagement(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get user engagement metrics"""
    user_id = current_user["user_id"]
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get engagement metrics
    engagement_result = await session.execute(
        text("""
            SELECT 
                COUNT(DISTINCT DATE(m.created_at)) as active_days,
                COUNT(m.id) as total_messages,
                COUNT(DISTINCT m.conversation_id) as conversations_participated,
                AVG(CHAR_LENGTH(m.content)) as avg_message_length
            FROM messages m
            WHERE m.user_id = %s AND m.created_at >= %s
        """),
        [user_id, start_date]
    )
    
    engagement_row = engagement_result.fetchone()
    
    # Calculate engagement score (simple heuristic)
    active_days = engagement_row.active_days or 0
    total_messages = engagement_row.total_messages or 0
    avg_message_length = float(engagement_row.avg_message_length or 0)
    
    engagement_score = min(100, (active_days / days * 40) + 
                          (min(total_messages, 100) / 100 * 40) + 
                          (min(avg_message_length, 200) / 200 * 20))
    
    return {
        "success": True,
        "period_days": days,
        "metrics": {
            "active_days": active_days,
            "total_messages": total_messages,
            "conversations_participated": engagement_row.conversations_participated or 0,
            "avg_message_length": round(avg_message_length, 1),
            "engagement_score": round(engagement_score, 1)
        }
    } 