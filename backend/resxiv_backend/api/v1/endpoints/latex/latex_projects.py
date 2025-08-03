"""
LaTeX Project Management Endpoints - L6 Engineering Standards
Focused on LaTeX project creation, management, and configuration.
"""

import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required, verify_project_access
)
from app.services.git_service import GitService
from app.services.branch_service import BranchService
from app.services.core.project_service_core import ProjectCoreService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects/{project_id}/latex/create", response_model=Dict[str, Any])
async def create_latex_project(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    template: str = Query("article", description="LaTeX template type"),
    name: str = Query(..., description="LaTeX project name"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Create a new LaTeX project within a ResXiv project.
    
    - **project_id**: Parent project UUID
    - **template**: LaTeX template type (article, report, book, beamer)
    - **name**: Name for the LaTeX project
    
    Creates the LaTeX project structure with initial template files.
    """
    try:
        # Initialize services
        git_service = GitService(session)
        branch_service = BranchService(session)
        project_service = ProjectCoreService(session)
        
        # Validate template type
        valid_templates = ["article", "report", "book", "beamer"]
        if template not in valid_templates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template. Must be one of: {', '.join(valid_templates)}"
            )
        
        # Generate LaTeX project structure
        latex_files = _get_template_files(template, name)
        
        # Create LaTeX project in git repository
        result = await git_service.create_latex_project(
            project_id=project_id,
            latex_name=name,
            template=template,
            files=latex_files,
            created_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Create default branch for LaTeX project
        import re
        from app.models.branch import BranchCreate

        raw_branch_name = f"latex-{name}"
        # Replace invalid characters with hyphen and collapse repeats
        safe_branch_name = re.sub(r"[^A-Za-z0-9_-]+", "-", raw_branch_name)
        safe_branch_name = re.sub(r"-+", "-", safe_branch_name).strip("-_").lower()

        branch_data = BranchCreate(
            name=safe_branch_name,
            description=f"LaTeX project: {name}"
        )
        branch_result = await branch_service.create_branch(
            project_id=project_id,
            branch_data=branch_data,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "latex_project": result["latex_project"],
            "branch": branch_result.get("branch") if branch_result.get("success") else None,
            "files_created": list(latex_files.keys()),
            "message": f"LaTeX project '{name}' created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating LaTeX project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create LaTeX project"
        )


@router.get("/projects/{project_id}/latex", response_model=Dict[str, Any])
async def get_latex_projects(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get all LaTeX projects for a ResXiv project.
    
    Returns list of LaTeX projects with their status and metadata.
    """
    try:
        git_service = GitService(session)
        
        # Get LaTeX projects from git repository
        result = await git_service.get_latex_projects(
            project_id=project_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "latex_projects": result["latex_projects"],
            "total_count": len(result["latex_projects"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LaTeX projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LaTeX projects"
        )


@router.get("/projects/{project_id}/latex/{latex_id}", response_model=Dict[str, Any])
async def get_latex_project_details(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    latex_id: str = Path(..., description="LaTeX project ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get detailed information about a specific LaTeX project.
    
    Returns project structure, compilation status, and metadata.
    """
    try:
        git_service = GitService(session)
        
        # Get LaTeX project details
        result = await git_service.get_latex_project_details(
            project_id=project_id,
            latex_id=latex_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "latex_project": result["latex_project"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LaTeX project details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LaTeX project details"
        )


@router.delete("/projects/{project_id}/latex/{latex_id}", response_model=Dict[str, Any])
async def delete_latex_project(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    latex_id: str = Path(..., description="LaTeX project ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Delete a LaTeX project.
    
    Removes the LaTeX project and all associated files.
    Requires admin access to the parent project.
    """
    try:
        git_service = GitService(session)
        
        # Delete LaTeX project
        result = await git_service.delete_latex_project(
            project_id=project_id,
            latex_id=latex_id,
            deleted_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": f"LaTeX project '{latex_id}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LaTeX project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete LaTeX project"
        )


def _get_template_files(template: str, project_name: str) -> Dict[str, str]:
    """Generate LaTeX template files based on template type."""
    
    if template == "article":
        main_tex = r"""\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsfonts,amssymb}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{hyperref}

\title{PROJECT_NAME}
\author{ResXiv Collaborative Project}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
This is the abstract of your research paper. Describe the main contributions and findings here.
\end{abstract}

\section{Introduction}
Write your introduction here.

\section{Methods}
Describe your methodology here.

\section{Results}
Present your results here.

\section{Conclusion}
Summarize your findings and conclude here.

\bibliographystyle{plain}
\bibliography{references}

\end{document}""".replace("PROJECT_NAME", project_name)

        references_bib = """@article{example2024,
    title={Example Paper Title},
    author={Author, First and Author, Second},
    journal={Journal Name},
    volume={1},
    number={1},
    pages={1--10},
    year={2024},
    publisher={Publisher}
}"""

        return {
            "main.tex": main_tex,
            "references.bib": references_bib
        }
    
    elif template == "report":
        main_tex = r"""\documentclass[12pt]{report}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsfonts,amssymb}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{hyperref}

\title{PROJECT_NAME}
\author{ResXiv Collaborative Project}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
This is the abstract of your research report.
\end{abstract}

\tableofcontents

\chapter{Introduction}
Write your introduction here.

\chapter{Background}
Provide background information here.

\chapter{Analysis}
Present your analysis here.

\chapter{Conclusion}
Summarize your findings here.

\bibliographystyle{plain}
\bibliography{references}

\end{document}""".replace("PROJECT_NAME", project_name)

        return {
            "main.tex": main_tex,
            "references.bib": """@book{example2024,
    title={Example Book Title},
    author={Author, First},
    publisher={Publisher},
    year={2024}
}"""
        }
    
    elif template == "book":
        main_tex = r"""\documentclass[12pt]{book}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsfonts,amssymb}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{hyperref}

\title{PROJECT_NAME}
\author{ResXiv Collaborative Project}
\date{\today}

\begin{document}

\frontmatter
\maketitle
\tableofcontents

\mainmatter

\part{Part One}

\chapter{Introduction}
Write your introduction here.

\chapter{Background}
Provide background information here.

\part{Part Two}

\chapter{Main Content}
Present your main content here.

\chapter{Advanced Topics}
Discuss advanced topics here.

\backmatter

\appendix
\chapter{Appendix}
Additional material here.

\bibliographystyle{plain}
\bibliography{references}

\end{document}""".replace("PROJECT_NAME", project_name)

        return {
            "main.tex": main_tex,
            "references.bib": """@book{example2024,
    title={Example Reference Book},
    author={Author, First},
    publisher={Academic Press},
    year={2024}
}"""
        }
    
    elif template == "beamer":
        main_tex = r"""\documentclass{beamer}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}

\usetheme{Madrid}
\usecolortheme{default}

\title{PROJECT_NAME}
\author{ResXiv Collaborative Project}
\institute{ResXiv Platform}
\date{\today}

\begin{document}

\frame{\titlepage}

\begin{frame}
\frametitle{Outline}
\tableofcontents
\end{frame}

\section{Introduction}
\begin{frame}
\frametitle{Introduction}
\begin{itemize}
    \item Introduction point 1
    \item Introduction point 2
    \item Introduction point 3
\end{itemize}
\end{frame}

\section{Main Content}
\begin{frame}
\frametitle{Main Content}
\begin{itemize}
    \item Main point 1
    \item Main point 2
    \item Main point 3
\end{itemize}
\end{frame}

\section{Conclusion}
\begin{frame}
\frametitle{Conclusion}
\begin{itemize}
    \item Conclusion point 1
    \item Conclusion point 2
    \item Thank you for your attention!
\end{itemize}
\end{frame}

\end{document}""".replace("PROJECT_NAME", project_name)

        return {
            "main.tex": main_tex
        }
    
    else:
        # Default to article template
        return _get_template_files("article", project_name) 