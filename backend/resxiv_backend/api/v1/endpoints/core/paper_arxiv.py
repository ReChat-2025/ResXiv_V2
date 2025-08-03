"""
ArXiv Integration Endpoints
L6 Engineering Standards - Focused module for ArXiv search and download functionality
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required
from app.services.paper_service import PaperService
from app.models.paper import ArXivSearchRequest, ArXivDownloadRequest
from app.core.error_handling import handle_service_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/arxiv/search", response_model=Dict[str, Any], tags=["ArXiv"])
@handle_service_errors("ArXiv search")
async def search_arxiv(
    search_request: ArXivSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Search ArXiv for papers
    
    - **query**: Search query
    - **max_results**: Maximum number of results (1-100)
    - **sort_by**: Sort criteria (relevance, lastUpdatedDate, submittedDate)
    - **sort_order**: Sort order (ascending, descending)
    - **categories**: Optional ArXiv categories to filter
    
    Returns list of ArXiv papers matching the search criteria.
    """
    paper_service = PaperService(session)
    
    result = await paper_service.search_arxiv(search_request)
    
    return {
        "success": True,
        "papers": result["papers"],
        "total": result["total"],
        "query": search_request.query,
        "search_metadata": {
            "max_results": search_request.max_results,
            "sort_by": search_request.sort_by,
            "sort_order": search_request.sort_order,
            "categories": search_request.categories
        }
    }


@router.post("/arxiv/download", response_model=Dict[str, Any], tags=["ArXiv"])
@handle_service_errors("ArXiv download")
async def download_arxiv_paper(
    download_request: ArXivDownloadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Download a paper from ArXiv and add it to a project
    
    - **arxiv_id**: ArXiv paper ID (e.g., "2301.12345")
    - **project_id**: Project UUID to add the paper to
    - **process_with_grobid**: Whether to process with GROBID for metadata extraction
    - **run_diagnostics**: Whether to run LLM diagnostics
    
    Returns the downloaded paper information.
    """
    paper_service = PaperService(session)
    
    result = await paper_service.download_arxiv_paper(
        arxiv_id=download_request.arxiv_id,
        project_id=download_request.project_id,
        user_id=current_user["user_id"],
        process_with_grobid=download_request.process_with_grobid,
        run_diagnostics=download_request.run_diagnostics
    )
    
    return {
        "success": True,
        "message": result["message"],
        "paper_id": result["paper_id"],
        "arxiv_id": download_request.arxiv_id,
        "processing_status": result.get("processing_status"),
        "diagnostic_status": result.get("diagnostic_status")
    }


@router.get("/arxiv/categories", response_model=List[Dict[str, str]], tags=["ArXiv"])
@handle_service_errors("ArXiv categories")
async def get_arxiv_categories(
    current_user: Dict[str, Any] = Depends(get_current_user_required)
):
    """
    Get list of available ArXiv categories
    
    Returns all available ArXiv subject categories for filtering searches.
    """
    # Static list of ArXiv categories
    categories = [
        {"id": "cs.AI", "name": "Artificial Intelligence"},
        {"id": "cs.CL", "name": "Computation and Language"},
        {"id": "cs.CV", "name": "Computer Vision and Pattern Recognition"},
        {"id": "cs.LG", "name": "Machine Learning"},
        {"id": "cs.NE", "name": "Neural and Evolutionary Computing"},
        {"id": "cs.RO", "name": "Robotics"},
        {"id": "stat.ML", "name": "Machine Learning (Statistics)"},
        {"id": "math.ST", "name": "Statistics Theory"},
        {"id": "physics.data-an", "name": "Data Analysis, Statistics and Probability"},
        {"id": "q-bio.QM", "name": "Quantitative Methods"},
        {"id": "econ.EM", "name": "Econometrics"},
        {"id": "astro-ph.IM", "name": "Instrumentation and Methods for Astrophysics"},
        {"id": "cond-mat.stat-mech", "name": "Statistical Mechanics"},
        {"id": "hep-th", "name": "High Energy Physics - Theory"},
        {"id": "math-ph", "name": "Mathematical Physics"},
        {"id": "nlin.CD", "name": "Chaotic Dynamics"},
        {"id": "quant-ph", "name": "Quantum Physics"}
    ]
    
    return categories 