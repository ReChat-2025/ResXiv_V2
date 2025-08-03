"""
API Router Configuration

Aggregates all API endpoints and organizes them by version.
This file serves as the main entry point for all API routes.
"""

from fastapi import APIRouter

# Import all endpoint routers
from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.papers_consolidated import router as papers_router
# from api.v1.endpoints.users import router as users_router  # Covered by auth.py
from api.v1.endpoints.projects import router as projects_router
from api.v1.endpoints.tasks import router as tasks_router
from api.v1.endpoints.conversations import router as conversations_router
from api.v1.endpoints.branches import router as branches_router
from api.v1.endpoints.graphs import router as graphs_router
from api.v1.endpoints.latex import router as latex_router
from api.v1.endpoints.analytics import router as analytics_router
from api.v1.endpoints.files import router as files_router
from api.v1.endpoints.search import router as search_router
from api.v1.endpoints.journals import router as journals_router

# Create main API router
api_router = APIRouter()

# Health check endpoint at API level
@api_router.get("/health", tags=["API Health"])
async def api_health():
    """API-level health check"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "message": "ResXiv API is running"
    }

# Include all endpoint routers
# Note: These are commented out as the endpoints haven't been created yet
# Uncomment as endpoints are implemented

# Authentication routes
api_router.include_router(auth_router, prefix="/auth", tags=["User"])

# User management routes - handled by auth.py
# api_router.include_router(users_router, prefix="/users", tags=["Users"])

# Project management routes
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])

# Paper management routes - nested under projects
api_router.include_router(papers_router, prefix="/projects", tags=["Papers"])

# Task management routes - nested under projects
api_router.include_router(tasks_router, prefix="/projects", tags=["Tasks"])

# Conversation/messaging routes
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])

# Branch and collaborative editing routes
api_router.include_router(branches_router, prefix="/projects", tags=["Branches"])

# Agentic system routes - production version
from api.v1.endpoints.agentic_production import router as agentic_production_router
api_router.include_router(agentic_production_router, prefix="/agentic", tags=["Agentic System"])

# Graph generation and management routes
api_router.include_router(graphs_router, prefix="/graphs", tags=["Graphs"])

# LaTeX editor routes
api_router.include_router(latex_router, prefix="/latex", tags=["LaTeX"])

# Analytics and reporting routes
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

# File management routes
api_router.include_router(files_router, prefix="/files", tags=["Files"])

# Unified search routes
api_router.include_router(search_router, prefix="/search", tags=["Search"])

# Journal management routes
api_router.include_router(journals_router, prefix="/journals", tags=["Journals"])

# FUTURE ENHANCEMENTS (when needed):
# - Enhanced AI/LLM integration routes (partially covered by agentic.py)
# - Additional external API integration routes (ArXiv covered in papers.py)
# - Advanced WebSocket routes for real-time features (basic WebSocket covered)
# - Push notification routes
# - Advanced visualization routes

# COMPLETED ENDPOINTS:
# ✅ Authentication & User Management (auth.py)
# ✅ Paper Management (papers.py) 
# ✅ Project Management (projects.py)
# ✅ Task Management (tasks.py)
# ✅ Conversations & Messaging (conversations.py)
# ✅ Version Control & Collaboration (branches.py)
# ✅ AI Agent System (agentic.py)
# ✅ Graph Generation (graphs.py)
# ✅ LaTeX Editor (latex.py)
# ✅ Analytics & Reporting (analytics.py)
# ✅ File Management (files.py)
# ✅ Unified Search (search.py)
# ✅ Journal Management (journals.py) 