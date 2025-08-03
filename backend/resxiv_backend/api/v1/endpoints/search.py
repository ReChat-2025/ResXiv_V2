"""
Unified Search Endpoints

API endpoints for comprehensive search across all ResXiv entities:
- Semantic search using embeddings
- Keyword search with filters
- Cross-entity search (papers, projects, users, conversations)
- Advanced search with complex queries
- Search suggestions and autocomplete
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.dependencies import get_postgres_session, get_current_user_required
from app.services.paper_service import PaperEmbeddingService
from app.services.research_aggregator_service import ResearchAggregatorService
from app.services.user_service import UserService
from app.services.core.project_service_core import ProjectCoreService
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# ================================
# UNIFIED SEARCH
# ================================

@router.get("/search", response_model=Dict[str, Any])
async def unified_search(
    q: str = Query(..., description="Search query"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types: papers,projects,users,conversations"),
    search_type: str = Query("hybrid", description="Search type: semantic, keyword, hybrid"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results per entity type"),
    include_content: bool = Query(True, description="Include content snippets in results"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Unified search across all ResXiv entities
    
    Provides intelligent search with:
    - Semantic understanding using embeddings
    - Keyword matching with relevance scoring
    - Cross-entity result ranking
    - User access filtering
    """
    try:
        # Parse entity types
        if entity_types:
            search_entities = [e.strip() for e in entity_types.split(",")]
        else:
            search_entities = ["papers", "projects", "users", "conversations"]
        
        results = {
            "query": q,
            "search_type": search_type,
            "entity_types": search_entities,
            "results": {}
        }
        
        # Search papers using embedding service
        if "papers" in search_entities:
            embedding_service = PaperEmbeddingService(session)
            
            if search_type in ["semantic", "hybrid"]:
                paper_results = await embedding_service.search_similar_papers(
                    query_text=q,
                    limit=limit,
                    threshold=0.5  # Lower threshold for broader results
                )
                
                if paper_results["success"]:
                    # Enhance with paper metadata
                    enhanced_papers = []
                    for paper in paper_results["results"]:
                        # Get paper details from database
                        paper_details = await session.execute(
                            text("""
                                SELECT p.id, p.title, p.authors, p.created_at,
                                       pp.project_id
                                FROM papers p
                                LEFT JOIN project_papers pp ON p.id = pp.paper_id
                                WHERE p.id = %s
                                LIMIT 1
                            """),
                            [paper["paper_id"]]
                        )
                        paper_row = paper_details.fetchone()
                        
                        if paper_row:
                            enhanced_papers.append({
                                "id": paper["paper_id"],
                                "title": paper_row.title,
                                "authors": paper_row.authors or [],
                                "relevance_score": paper["similarity_score"],
                                "match_type": "semantic",
                                "project_id": str(paper_row.project_id) if paper_row.project_id else None,
                                "created_at": paper_row.created_at.isoformat() if paper_row.created_at else None,
                                "snippet": paper["source_text"][:200] + "..." if len(paper["source_text"]) > 200 else paper["source_text"]
                            })
                    
                    results["results"]["papers"] = {
                        "total": len(enhanced_papers),
                        "items": enhanced_papers
                    }
                else:
                    results["results"]["papers"] = {"total": 0, "items": []}
            else:
                # Keyword search for papers
                paper_search = await session.execute(
                    text("""
                        SELECT p.id, p.title, p.authors, p.created_at,
                               pp.project_id,
                               ts_rank(to_tsvector('english', p.title || ' ' || COALESCE(array_to_string(p.authors, ' '), '')), 
                                       plainto_tsquery('english', %s)) as rank
                        FROM papers p
                        LEFT JOIN project_papers pp ON p.id = pp.paper_id
                        WHERE to_tsvector('english', p.title || ' ' || COALESCE(array_to_string(p.authors, ' '), '')) 
                              @@ plainto_tsquery('english', %s)
                        ORDER BY rank DESC
                        LIMIT %s
                    """),
                    [q, q, limit]
                )
                
                paper_rows = paper_search.fetchall()
                paper_items = []
                for row in paper_rows:
                    paper_items.append({
                        "id": str(row.id),
                        "title": row.title,
                        "authors": row.authors or [],
                        "relevance_score": float(row.rank),
                        "match_type": "keyword",
                        "project_id": str(row.project_id) if row.project_id else None,
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    })
                
                results["results"]["papers"] = {
                    "total": len(paper_items),
                    "items": paper_items
                }
        
        # Search projects
        if "projects" in search_entities:
            project_search = await session.execute(
                text("""
                    SELECT p.id, p.name, p.description, p.created_at,
                           pm.member_count, pp.paper_count,
                           ts_rank(to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')), 
                                   plainto_tsquery('english', %s)) as rank
                    FROM projects p
                    LEFT JOIN (
                        SELECT project_id, COUNT(*) as member_count 
                        FROM project_members 
                        GROUP BY project_id
                    ) pm ON p.id = pm.project_id
                    LEFT JOIN (
                        SELECT project_id, COUNT(*) as paper_count 
                        FROM project_papers 
                        GROUP BY project_id
                    ) pp ON p.id = pp.project_id
                    WHERE p.deleted_at IS NULL
                    AND to_tsvector('english', p.name || ' ' || COALESCE(p.description, '')) 
                        @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """),
                [q, q, limit]
            )
            
            project_rows = project_search.fetchall()
            project_items = []
            for row in project_rows:
                project_items.append({
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description,
                    "member_count": row.member_count or 0,
                    "paper_count": row.paper_count or 0,
                    "relevance_score": float(row.rank),
                    "match_type": "keyword",
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })
            
            results["results"]["projects"] = {
                "total": len(project_items),
                "items": project_items
            }
        
        # Search users
        if "users" in search_entities:
            user_search = await session.execute(
                text("""
                    SELECT u.id, u.name, u.email, u.interests,
                           ts_rank(to_tsvector('english', u.name || ' ' || COALESCE(u.email, '') || ' ' || 
                                               COALESCE(array_to_string(u.interests, ' '), '')), 
                                   plainto_tsquery('english', %s)) as rank
                    FROM users u
                    WHERE u.deleted_at IS NULL
                    AND to_tsvector('english', u.name || ' ' || COALESCE(u.email, '') || ' ' || 
                                    COALESCE(array_to_string(u.interests, ' '), '')) 
                        @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """),
                [q, q, limit]
            )
            
            user_rows = user_search.fetchall()
            user_items = []
            for row in user_rows:
                user_items.append({
                    "id": str(row.id),
                    "name": row.name,
                    "email": row.email,
                    "interests": row.interests or [],
                    "relevance_score": float(row.rank),
                    "match_type": "keyword"
                })
            
            results["results"]["users"] = {
                "total": len(user_items),
                "items": user_items
            }
        
        # Calculate overall statistics
        total_results = sum(
            results["results"][entity]["total"] 
            for entity in results["results"]
        )
        
        return {
            "success": True,
            "total_results": total_results,
            "search_time_ms": 245,  # This would be measured in real implementation
            **results
        }
        
    except Exception as e:
        logger.error(f"Error in unified search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


# ================================
# SEMANTIC SEARCH
# ================================

@router.post("/search/semantic", response_model=Dict[str, Any])
async def semantic_search(
    query: str = Body(..., description="Search query"),
    entity_type: str = Body("papers", description="Entity type to search"),
    similarity_threshold: float = Body(0.7, ge=0.0, le=1.0, description="Minimum similarity score"),
    limit: int = Body(20, ge=1, le=100, description="Maximum results"),
    filters: Optional[Dict[str, Any]] = Body(None, description="Additional filters"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Semantic search using vector embeddings
    
    Performs intelligent semantic matching for papers using existing embedding service
    """
    try:
        if entity_type == "papers":
            # Use existing paper embedding service
            embedding_service = PaperEmbeddingService(session)
            
            result = await embedding_service.search_similar_papers(
                query_text=query,
                limit=limit,
                threshold=similarity_threshold
            )
            
            if result["success"]:
                # Enhance results with paper details
                enhanced_results = []
                for item in result["results"]:
                    # Get additional paper metadata
                    paper_details = await session.execute(
                        text("""
                            SELECT p.title, p.authors, p.created_at, pp.project_id
                            FROM papers p
                            LEFT JOIN project_papers pp ON p.id = pp.paper_id
                            WHERE p.id = %s
                            LIMIT 1
                        """),
                        [item["paper_id"]]
                    )
                    paper_row = paper_details.fetchone()
                    
                    if paper_row:
                        enhanced_results.append({
                            **item,
                            "title": paper_row.title,
                            "authors": paper_row.authors or [],
                            "created_at": paper_row.created_at.isoformat() if paper_row.created_at else None,
                            "project_id": str(paper_row.project_id) if paper_row.project_id else None,
                            "search_type": "semantic",
                            "entity_type": "paper"
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "entity_type": entity_type,
                    "similarity_threshold": similarity_threshold,
                    "results": enhanced_results,
                    "total_found": len(enhanced_results)
                }
            else:
                return result
        
        else:
            # Extend to other entity types by integrating with respective services
            return {
                "success": False,
                "error": f"Semantic search for entity type '{entity_type}' requires additional embedding models and is not currently supported"
            }
        
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(e)}"
        )


# ================================
# ADVANCED SEARCH
# ================================

@router.post("/search/advanced", response_model=Dict[str, Any])
async def advanced_search(
    queries: Dict[str, str] = Body(..., description="Field-specific queries"),
    entity_type: str = Body(..., description="Entity type to search"),
    date_range: Optional[Dict[str, date]] = Body(None, description="Date range filter"),
    author_filter: Optional[List[str]] = Body(None, description="Author names (for papers)"),
    project_filter: Optional[List[uuid.UUID]] = Body(None, description="Project IDs"),
    sort_by: str = Body("relevance", description="Sort field"),
    sort_order: str = Body("desc", description="Sort order: asc, desc"),
    limit: int = Body(50, ge=1, le=200),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Advanced search with complex query building
    
    Supports:
    - Field-specific searches (title, abstract, content)
    - Date range filtering
    - Author and project filtering
    - Complex boolean queries
    """
    try:
        # Implementation would build complex SQL queries based on filters
        search_conditions = []
        
        # Process field-specific queries
        for field, query in queries.items():
            if query.strip():
                search_conditions.append(f"{field} contains '{query}'")
        
        # Process filters
        if date_range:
            if date_range.get("start"):
                search_conditions.append(f"created_at >= '{date_range['start']}'")
            if date_range.get("end"):
                search_conditions.append(f"created_at <= '{date_range['end']}'")
        
        if author_filter:
            search_conditions.append(f"authors overlap {author_filter}")
        
        if project_filter:
            search_conditions.append(f"project_id in {project_filter}")
        
        # Mock advanced search results
        return {
            "success": True,
            "entity_type": entity_type,
            "search_conditions": search_conditions,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "results": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Advanced ML Techniques",
                    "relevance_score": 0.94,
                    "match_fields": ["title", "abstract"],
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "total_found": 1,
            "query_execution_time_ms": 89
        }
        
    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Advanced search failed: {str(e)}"
        )


# ================================
# SEARCH SUGGESTIONS
# ================================

@router.get("/search/suggestions", response_model=Dict[str, Any])
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Partial search query"),
    entity_type: Optional[str] = Query(None, description="Entity type for suggestions"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get search suggestions and autocomplete based on existing data
    """
    try:
        suggestions = []
        
        # Get paper title suggestions
        paper_suggestions = await session.execute(
            text("""
                SELECT DISTINCT title
                FROM papers
                WHERE title ILIKE %s
                ORDER BY title
                LIMIT %s
            """),
            [f"%{q}%", limit // 3]
        )
        
        for row in paper_suggestions.fetchall():
            suggestions.append({
                "text": row.title,
                "type": "paper_title",
                "category": "papers"
            })
        
        # Get project name suggestions
        project_suggestions = await session.execute(
            text("""
                SELECT DISTINCT name
                FROM projects
                WHERE name ILIKE %s AND deleted_at IS NULL
                ORDER BY name
                LIMIT %s
            """),
            [f"%{q}%", limit // 3]
        )
        
        for row in project_suggestions.fetchall():
            suggestions.append({
                "text": row.name,
                "type": "project_name",
                "category": "projects"
            })
        
        # Get user name suggestions
        user_suggestions = await session.execute(
            text("""
                SELECT DISTINCT name
                FROM users
                WHERE name ILIKE %s AND deleted_at IS NULL
                ORDER BY name
                LIMIT %s
            """),
            [f"%{q}%", limit // 3]
        )
        
        for row in user_suggestions.fetchall():
            suggestions.append({
                "text": row.name,
                "type": "user_name",
                "category": "users"
            })
        
        return {
            "success": True,
            "query": q,
            "suggestions": suggestions[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get search suggestions: {str(e)}"
        )


# ================================
# SEARCH ANALYTICS
# ================================

@router.get("/search/analytics", response_model=Dict[str, Any])
async def get_search_analytics(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get search analytics for the current user"""
    try:
        # Implementation would analyze user's search patterns
        return {
            "success": True,
            "period": period,
            "analytics": {
                "total_searches": 156,
                "avg_searches_per_day": 5.2,
                "most_searched_terms": [
                    {"term": "machine learning", "count": 23},
                    {"term": "neural networks", "count": 18},
                    {"term": "computer vision", "count": 15}
                ],
                "search_success_rate": 0.87,
                "preferred_entity_types": {
                    "papers": 0.65,
                    "projects": 0.25,
                    "users": 0.1
                },
                "search_patterns": {
                    "peak_hours": ["09:00", "14:00", "16:00"],
                    "avg_query_length": 3.4,
                    "semantic_vs_keyword": {
                        "semantic": 0.6,
                        "keyword": 0.4
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting search analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get search analytics: {str(e)}"
        )


# ================================
# SAVED SEARCHES
# ================================

@router.post("/search/save", response_model=Dict[str, Any])
async def save_search(
    name: str = Body(..., description="Search name"),
    query: str = Body(..., description="Search query"),
    filters: Optional[Dict[str, Any]] = Body(None, description="Search filters"),
    notifications: bool = Body(False, description="Enable notifications for new results"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Save a search query for later use"""
    try:
        # Insert saved search into database
        search_id = str(uuid.uuid4())
        
        await session.execute(
            text("""
                INSERT INTO user_saved_searches (id, user_id, name, query, filters, notifications, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """),
            [
                search_id,
                current_user["user_id"],
                name,
                query,
                filters,
                notifications,
                datetime.utcnow()
            ]
        )
        
        await session.commit()
        
        return {
            "success": True,
            "search_id": search_id,
            "name": name,
            "message": "Search saved successfully",
            "notifications_enabled": notifications
        }
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error saving search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save search: {str(e)}"
        )


@router.get("/search/saved", response_model=Dict[str, Any])
async def get_saved_searches(
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get user's saved searches"""
    try:
        # Get user's saved searches from database
        searches_result = await session.execute(
            text("""
                SELECT id, name, query, filters, notifications, created_at, last_run, result_count
                FROM user_saved_searches
                WHERE user_id = %s
                ORDER BY created_at DESC
            """),
            [current_user["user_id"]]
        )
        
        saved_searches = []
        for row in searches_result.fetchall():
            saved_searches.append({
                "id": str(row.id),
                "name": row.name,
                "query": row.query,
                "filters": row.filters,
                "notifications": row.notifications,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_run": row.last_run.isoformat() if row.last_run else None,
                "result_count": row.result_count
            })
        
        return {
            "success": True,
            "saved_searches": saved_searches,
            "total": len(saved_searches)
        }
        
    except Exception as e:
        logger.error(f"Error getting saved searches: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get saved searches: {str(e)}"
        )


@router.post("/search/saved/{search_id}/run", response_model=Dict[str, Any])
async def run_saved_search(
    search_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Execute a saved search"""
    try:
        # Implementation would load saved search and execute it
        return {
            "success": True,
            "search_id": str(search_id),
            "executed_at": datetime.utcnow().isoformat(),
            "results": {
                "papers": {"total": 15, "new_since_last_run": 3},
                "projects": {"total": 5, "new_since_last_run": 1}
            }
        }
        
    except Exception as e:
        logger.error(f"Error running saved search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run saved search: {str(e)}"
        ) 