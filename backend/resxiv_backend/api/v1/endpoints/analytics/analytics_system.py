"""
System Analytics Endpoints - L6 Engineering Standards

Focused module for system-wide analytics functionality.
Extracted from bloated analytics.py for SOLID compliance.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.dependencies import get_postgres_session, get_current_user_required
from app.core.error_handling import handle_service_errors, ErrorCodes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/system/metrics", response_model=Dict[str, Any])
@handle_service_errors("system metrics retrieval")
async def get_system_metrics(
    metric_category: Optional[str] = Query(None, description="Filter by metric category"),
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get system-wide performance and usage metrics
    
    Note: This should be admin-only in production
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Build query filter
    where_clause = "WHERE recorded_at >= %s"
    params = [start_time]
    
    if metric_category:
        where_clause += " AND metric_category = %s"
        params.append(metric_category)
    
    # Get performance metrics
    metrics_result = await session.execute(
        text(f"""
            SELECT 
                metric_name,
                metric_category,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                COUNT(*) as sample_count,
                unit
            FROM performance_metrics 
            {where_clause}
            GROUP BY metric_name, metric_category, unit
            ORDER BY metric_category, metric_name
        """),
        params
    )
    
    metrics = []
    for row in metrics_result.fetchall():
        metrics.append({
            "metric_name": row.metric_name,
            "category": row.metric_category,
            "avg_value": round(float(row.avg_value), 2),
            "min_value": round(float(row.min_value), 2),
            "max_value": round(float(row.max_value), 2),
            "sample_count": row.sample_count,
            "unit": row.unit
        })
    
    # Get basic system stats (PostgreSQL data only)
    system_stats_result = await session.execute(
        text("""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE deleted_at IS NULL) as total_users,
                (SELECT COUNT(*) FROM projects WHERE deleted_at IS NULL) as total_projects,
                (SELECT COUNT(*) FROM papers WHERE deleted_at IS NULL) as total_papers,
                0 as total_messages
        """)
    )
    
    stats_row = system_stats_result.fetchone()
    
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "time_range_hours": hours,
        "metric_category": metric_category,
        "performance_metrics": metrics,
        "system_stats": {
            "total_users": stats_row.total_users,
            "total_projects": stats_row.total_projects,
            "total_papers": stats_row.total_papers,
            "total_messages": stats_row.total_messages
        }
    }


@router.get("/system/health", response_model=Dict[str, Any])
@handle_service_errors("system health check")
async def get_system_health(
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get system health status"""
    start_time = datetime.utcnow()
    
    # Test database connectivity
    try:
        await session.execute(text("SELECT 1"))
        db_status = "healthy"
        db_response_time = (datetime.utcnow() - start_time).total_seconds()
    except Exception as e:
        db_status = "unhealthy"
        db_response_time = None
        logger.error(f"Database health check failed: {e}")
    
    # Get recent error counts
    error_result = await session.execute(
        text("""
            SELECT COUNT(*) as error_count
            FROM error_logs 
            WHERE created_at >= %s
        """),
        [datetime.utcnow() - timedelta(hours=1)]
    )
    
    error_row = error_result.fetchone()
    recent_errors = error_row.error_count if error_row else 0
    
    # Calculate overall health score
    health_score = 100
    if db_status != "healthy":
        health_score -= 50
    if recent_errors > 10:
        health_score -= min(recent_errors * 2, 40)
    
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "overall_health": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy",
        "health_score": max(health_score, 0),
        "components": {
            "database": {
                "status": db_status,
                "response_time_seconds": db_response_time
            },
            "error_rate": {
                "recent_errors_1h": recent_errors,
                "status": "healthy" if recent_errors < 5 else "warning" if recent_errors < 20 else "critical"
            }
        }
    } 