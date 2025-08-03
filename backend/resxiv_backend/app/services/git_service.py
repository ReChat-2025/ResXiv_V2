"""
Git Service - Production Implementation
L6 Engineering Standards - Proper Git repository management
"""

import logging
import subprocess
import asyncio
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
import json
import uuid
from datetime import datetime

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.branch import LaTeXFile, GitRepository
from app.repositories.branch_repository import BranchRepository

logger = logging.getLogger(__name__)


class GitService:
    """Production-grade Git repository management service"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """Accept optional DB session for database operations."""
        self.session = session
        self.branch_repository = BranchRepository(session) if session else None
        
        # Git repositories base directory
        default_git_dir = Path(__file__).parent.parent.parent.parent.parent / "repositories"
        self.git_base_dir = Path(default_git_dir)
        self.git_base_dir.mkdir(parents=True, exist_ok=True)
    
    @handle_service_errors("git status check")
    async def get_repository_status(self, repo_path: str) -> Dict[str, Any]:
        """
        Get Git repository status
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            Dict with repository status information
        """
        repo_path = Path(repo_path)
        
        if not repo_path.exists():
            return {
                "status": "not_found",
                "has_changes": False,
                "error": "Repository path does not exist"
            }
        
        if not (repo_path / ".git").exists():
            return {
                "status": "not_git_repo",
                "has_changes": False,
                "error": "Not a Git repository"
            }
        
        try:
            # Check for uncommitted changes
            result = await self._run_git_command(["status", "--porcelain"], str(repo_path))
            has_changes = bool(result.strip())
            
            # Get current branch
            branch_result = await self._run_git_command(["branch", "--show-current"], str(repo_path))
            current_branch = branch_result.strip()
            
            # Get last commit info
            try:
                commit_result = await self._run_git_command(
                    ["log", "-1", "--pretty=format:%H|%s|%an|%ad", "--date=iso"], 
                    str(repo_path)
                )
                commit_parts = commit_result.strip().split("|", 3)
                last_commit = {
                    "hash": commit_parts[0] if len(commit_parts) > 0 else None,
                    "message": commit_parts[1] if len(commit_parts) > 1 else None,
                    "author": commit_parts[2] if len(commit_parts) > 2 else None,
                    "date": commit_parts[3] if len(commit_parts) > 3 else None
                }
            except Exception:
                last_commit = None
            
            return {
                "status": "clean" if not has_changes else "dirty",
                "has_changes": has_changes,
                "current_branch": current_branch,
                "last_commit": last_commit,
                "repo_path": str(repo_path)
            }
            
        except Exception as e:
            logger.error(f"Git status check failed: {str(e)}")
            return {
                "status": "error",
                "has_changes": False,
                "error": str(e)
            }
    
    @handle_service_errors("git branch list")
    async def list_branches(self, repo_path: str) -> Dict[str, Any]:
        """
        List all branches in the repository
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            Dict with branch information
        """
        try:
            # Get all branches
            result = await self._run_git_command(["branch", "-a"], str(repo_path))
            
            branches = []
            current_branch = None
            
            for line in result.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                
                is_current = line.startswith("*")
                branch_name = line.lstrip("* ").replace("remotes/origin/", "")
                
                if is_current:
                    current_branch = branch_name
                
                if branch_name not in [b["name"] for b in branches]:
                    branches.append({
                        "name": branch_name,
                        "is_current": is_current,
                        "is_remote": "remotes/" in line
                    })
            
            return {
                "success": True,
                "branches": branches,
                "current_branch": current_branch,
                "total": len(branches)
            }
            
        except Exception as e:
            logger.error(f"Branch listing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "branches": [],
                "total": 0
            }
    
    @handle_service_errors("git commit")
    async def create_commit(
        self, 
        repo_path: str, 
        message: str, 
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Git commit
        
        Args:
            repo_path: Path to the Git repository
            message: Commit message
            author_name: Optional author name
            author_email: Optional author email
            
        Returns:
            Dict with commit information
        """
        try:
            # Stage all changes
            await self._run_git_command(["add", "."], str(repo_path))

            # Check if there are any changes to commit
            status_result = await self._run_git_command(["status", "--porcelain"], str(repo_path))
            if not status_result.strip():
                logger.info(f"No changes to commit in {repo_path}")
                # Get existing commit hash if available
                try:
                    hash_result = await self._run_git_command(["rev-parse", "HEAD"], str(repo_path))
                    commit_hash = hash_result.strip()
                    return {"success": True, "commit_hash": commit_hash, "message": "No changes to commit", "output": ""}
                except:
                    # No commits yet, this will be the first commit
                    pass

            async def _do_commit() -> str:
                commit_cmd = ["commit", "-m", message]
                if author_name and author_email:
                    commit_cmd.extend(["--author", f"{author_name} <{author_email}>"])
                return await self._run_git_command(commit_cmd, str(repo_path))

            try:
                result = await _do_commit()
            except ServiceError as se:
                # Auto-configure git user if missing and retry once
                if "user.email" in str(se) or "user.name" in str(se):
                    await self._run_git_command(["config", "user.name", author_name or "ResXiv User"], str(repo_path))
                    await self._run_git_command(["config", "user.email", author_email or "user@resxiv.local"], str(repo_path))
                    result = await _do_commit()
                else:
                    raise

            # Get the commit hash
            hash_result = await self._run_git_command(["rev-parse", "HEAD"], str(repo_path))
            commit_hash = hash_result.strip()

            return {"success": True, "commit_hash": commit_hash, "message": message, "output": result}

        except Exception as e:
            logger.error(f"Commit creation failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # --- LaTeX TEMPLATE OPERATIONS -------------------------------------------------
    
    async def get_custom_latex_templates(
        self,
        user_id: str,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get custom LaTeX templates for a user."""
        if not self.session:
            return {"success": True, "templates": []}
            
        try:
            # For now, return empty list - custom templates would be stored in a templates table
            # Future enhancement: implement custom template storage
            logger.debug(f"Getting custom templates for user {user_id}")
            return {"success": True, "templates": []}
        except Exception as e:
            logger.error(f"Error getting custom templates: {str(e)}")
            return {"success": False, "error": str(e), "templates": []}

    async def get_latex_template_details(
        self,
        template_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get details for a custom template."""
        if not self.session:
            return {"success": False, "error": "Template not found"}
            
        try:
            # For now, return not found - custom templates would be stored in a templates table
            logger.debug(f"Getting template details for {template_id}")
            return {"success": False, "error": "Template not found"}
        except Exception as e:
            logger.error(f"Error getting template details: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_latex_projects(
        self,
        project_id,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get LaTeX projects (file collections) for a project."""
        if not self.session:
            return {"success": True, "latex_projects": []}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Get git repository for project
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": True, "latex_projects": []}
            
            # Get LaTeX files for project (grouped as "projects")
            files_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.deleted_at.is_(None)
                )
            )
            latex_files = files_result.scalars().all()
            
            # Group files by directory prefix to simulate "latex projects"
            project_groups = {}
            for file in latex_files:
                # Extract project name from file path (e.g., "project1/main.tex" -> "project1")
                path_parts = file.file_path.split('/')
                project_name = path_parts[0] if len(path_parts) > 1 else "main"
                
                if project_name not in project_groups:
                    project_groups[project_name] = {
                        "id": f"{project_id_str}_{project_name}",
                        "name": project_name,
                        "template": "article",  # Default template
                        "created_at": file.created_at.isoformat(),
                        "created_by": str(file.created_by),
                        "files": []
                    }
                
                project_groups[project_name]["files"].append({
                    "id": str(file.id),
                    "path": file.file_path,
                    "name": file.file_name,
                    "type": file.file_type,
                    "size": file.file_size,
                    "updated_at": file.updated_at.isoformat()
                })
            
            latex_projects = list(project_groups.values())
            
            return {
                "success": True,
                "latex_projects": latex_projects
            }
            
        except Exception as e:
            logger.error(f"Error getting LaTeX projects: {str(e)}")
            return {"success": False, "error": str(e), "latex_projects": []}

    async def create_latex_project(
        self,
        project_id,
        latex_name: str,
        template: str,
        files: Dict[str, str],
        created_by: str,
    ) -> Dict[str, Any]:
        """Create a new LaTeX project with template files."""
        if not self.session:
            return {"success": False, "error": "Database session required"}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Get git repository for project
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": False, "error": "Git repository not found"}
            
            # Verify git repository exists and is properly initialized
            repo_path = Path(git_repo.repo_path)
            if not repo_path.exists():
                logger.error(f"Repository path does not exist: {repo_path}")
                return {"success": False, "error": "Repository path does not exist"}
            
            if not (repo_path / ".git").exists():
                logger.error(f"Not a git repository: {repo_path}")
                return {"success": False, "error": "Not a git repository"}
            
            logger.info(f"Using git repository: {repo_path}")
            
            # Check if LaTeX project already exists
            existing_files_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.file_path.like(f"{latex_name}/%"),
                    LaTeXFile.deleted_at.is_(None)
                )
            )
            existing_files = existing_files_result.scalars().all()
            
            if existing_files:
                logger.info(f"LaTeX project '{latex_name}' already exists with {len(existing_files)} files")
                return {
                    "success": True,
                    "latex_project": {
                        "id": f"{project_id_str}_{latex_name}",
                        "name": latex_name,
                        "template": template,
                        "files": [f.file_name for f in existing_files],
                        "message": "LaTeX project already exists"
                    }
                }
            
            latex_dir = repo_path / latex_name
            latex_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created LaTeX directory: {latex_dir}")
            
            # Create template files
            created_files = []
            for filename, content in files.items():
                file_path = latex_dir / filename
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"Created file: {file_path} ({len(content)} bytes)")
                
                # Create database record
                latex_file = LaTeXFile(
                    project_id=project_uuid,
                    branch_id=git_repo.default_branch_id,  # Use default branch
                    file_path=f"{latex_name}/{filename}",
                    file_name=filename,
                    file_type=filename.split('.')[-1] if '.' in filename else 'tex',
                    file_size=len(content.encode('utf-8')),
                    created_by=uuid.UUID(created_by),
                    last_modified_by=uuid.UUID(created_by)
                )
                self.session.add(latex_file)
                created_files.append(filename)
            
            logger.info(f"About to commit files to git in: {repo_path}")
            # Commit files to git
            commit_result = await self.create_commit(
                str(repo_path),
                f"Create LaTeX project: {latex_name}",
                "ResXiv System",
                "system@resxiv.com"
            )
            logger.info(f"Commit result: {commit_result}")
            
            await self.session.commit()
            
            return {
                "success": True,
                "latex_project": {
                    "id": f"{project_id_str}_{latex_name}",
                    "name": latex_name,
                    "template": template,
                    "files": created_files,
                    "commit_hash": commit_result.get("commit_hash") if commit_result.get("success") else None
                }
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating LaTeX project: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_latex_project_details(
        self,
        project_id,
        latex_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get details for a specific LaTeX project."""
        if not self.session:
            return {"success": False, "error": "Database session required"}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Extract latex name from latex_id (format: project_id_latex_name)
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            
            # Get LaTeX files for this project
            files_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.file_path.like(f"{latex_name}/%"),
                    LaTeXFile.deleted_at.is_(None)
                )
            )
            latex_files = files_result.scalars().all()
            
            if not latex_files:
                return {"success": False, "error": "LaTeX project not found"}
            
            files_data = []
            for file in latex_files:
                files_data.append({
                    "id": str(file.id),
                    "path": file.file_path,
                    "name": file.file_name,
                    "type": file.file_type,
                    "size": file.file_size,
                    "created_at": file.created_at.isoformat(),
                    "updated_at": file.updated_at.isoformat()
                })
            
            return {
                "success": True,
                "latex_project": {
                    "id": latex_id,
                    "name": latex_name,
                    "files": files_data,
                    "file_count": len(files_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting LaTeX project details: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_latex_project(
        self,
        project_id,
        latex_id: str,
        deleted_by: str,
    ) -> Dict[str, Any]:
        """Delete a LaTeX project and its files."""
        if not self.session:
            return {"success": False, "error": "Database session required"}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Extract latex name from latex_id
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            
            # Soft delete LaTeX files in database
            files_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.file_path.like(f"{latex_name}/%"),
                    LaTeXFile.deleted_at.is_(None)
                )
            )
            latex_files = files_result.scalars().all()
            
            for file in latex_files:
                file.deleted_at = datetime.utcnow()
                file.last_modified_by = uuid.UUID(deleted_by)
            
            # Get git repository and remove files
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if git_repo:
                repo_path = Path(git_repo.repo_path)
                latex_dir = repo_path / latex_name
                
                if latex_dir.exists():
                    import shutil
                    shutil.rmtree(latex_dir)
                    
                    # Commit deletion
                    await self.create_commit(
                        str(repo_path),
                        f"Delete LaTeX project: {latex_name}",
                        "ResXiv System",
                        "system@resxiv.com"
                    )
            
            await self.session.commit()
            
            return {"success": True}
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting LaTeX project: {str(e)}")
            return {"success": False, "error": str(e)}
 
    async def get_latex_files(
        self,
        project_id,
        latex_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get files and structure for a specific LaTeX project."""
        if not self.session:
            return {"success": False, "error": "Database session required"}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Extract latex name from latex_id
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            
            # Get LaTeX files from database
            files_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.file_path.like(f"{latex_name}/%"),
                    LaTeXFile.deleted_at.is_(None)
                ).order_by(LaTeXFile.file_path)
            )
            latex_files = files_result.scalars().all()
            
            if not latex_files:
                return {"success": False, "error": "LaTeX project not found"}
            
            # Build file structure
            files = []
            structure = {"name": latex_name, "type": "folder", "children": []}
            
            for file in latex_files:
                # Remove latex_name prefix from path
                relative_path = file.file_path.replace(f"{latex_name}/", "")
                
                files.append({
                    "id": str(file.id),
                    "name": file.file_name,
                    "path": relative_path,
                    "full_path": file.file_path,
                    "type": file.file_type,
                    "size": file.file_size,
                    "created_at": file.created_at.isoformat(),
                    "updated_at": file.updated_at.isoformat(),
                    "created_by": str(file.created_by),
                    "encoding": file.encoding
                })
                
                # Add to structure tree
                structure["children"].append({
                    "name": file.file_name,
                    "type": "file",
                    "path": relative_path,
                    "size": file.file_size,
                    "last_modified": file.updated_at.isoformat()
                })
            
            return {
                "success": True,
                "files": files,
                "structure": structure,
                "last_modified": max(f["updated_at"] for f in files) if files else None
            }
            
        except Exception as e:
            logger.error(f"Error getting LaTeX files: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_latex_file_content(
        self,
        project_id,
        latex_id: str,
        file_path: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get content of a specific LaTeX file."""
        if not self.session:
            return {"success": False, "error": "Database session required"}
            
        try:
            # Convert to UUID if string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Extract latex name from latex_id
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            
            # Construct full file path
            full_file_path = f"{latex_name}/{file_path}"
            
            # Get file from database
            file_result = await self.session.execute(
                select(LaTeXFile).where(
                    LaTeXFile.project_id == project_uuid,
                    LaTeXFile.file_path == full_file_path,
                    LaTeXFile.deleted_at.is_(None)
                )
            )
            latex_file = file_result.scalar_one_or_none()
            
            if not latex_file:
                return {"success": False, "error": "File not found"}
            
            # Get git repository
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": False, "error": "Git repository not found"}
            
            # Read file content from filesystem. Support legacy layout that had an extra "file" directory.
            repo_path = Path(git_repo.repo_path)
            file_full_path = repo_path / full_file_path

            # Legacy support: earlier versions saved into <repo>/file/<latex_root>/...
            legacy_file_path = repo_path / "file" / full_file_path

            if file_full_path.exists():
                path_to_read = file_full_path
            elif legacy_file_path.exists():
                # Fallback to legacy path so existing projects still work
                path_to_read = legacy_file_path
            else:
                return {"success": False, "error": "File not found on filesystem"}
            
            try:
                content = path_to_read.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"Error reading file {path_to_read}: {str(e)}")
                return {"success": False, "error": "Error reading file"}
            
            return {
                "success": True,
                "content": content,
                "file_info": {
                    "id": str(latex_file.id),
                    "name": latex_file.file_name,
                    "path": file_path,
                    "full_path": latex_file.file_path,
                    "type": latex_file.file_type,
                    "size": latex_file.file_size,
                    "encoding": latex_file.encoding,
                    "created_at": latex_file.created_at.isoformat(),
                    "updated_at": latex_file.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting LaTeX file content: {str(e)}")
            return {"success": False, "error": str(e)}

    @handle_service_errors("LaTeX compilation")
    async def compile_latex_project(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        main_file: str = "main.tex",
        output_format: str = "pdf",
        engine: str = "pdflatex",
        compiled_by: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Compile LaTeX project to PDF or other formats.
        
        Args:
            project_id: Project UUID
            latex_id: LaTeX project identifier
            main_file: Main LaTeX file to compile
            output_format: Output format (pdf, dvi, ps)
            engine: LaTeX engine to use
            compiled_by: User ID who initiated compilation
            
        Returns:
            Dict with success status and compilation info
        """
        try:
            # Convert project_id to UUID and string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Generate compilation ID
            compilation_id = str(uuid.uuid4())
            
            # Get git repository
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": False, "error": "Git repository not found"}
            
            # Extract latex name from latex_id
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            
            # Set up paths with legacy support
            repo_path = Path(git_repo.repo_path)
            latex_dir = repo_path / latex_name
            main_file_path = latex_dir / main_file
            
            # Legacy support: check if files are in old "file" subdirectory
            legacy_latex_dir = repo_path / "file" / latex_name
            legacy_main_file_path = legacy_latex_dir / main_file
            
            if latex_dir.exists():
                source_dir = latex_dir
            elif legacy_latex_dir.exists():
                # Use legacy path
                source_dir = legacy_latex_dir
                main_file_path = legacy_main_file_path
            else:
                return {"success": False, "error": f"LaTeX project directory not found: {latex_name}"}
            
            if not main_file_path.exists():
                # Fallback: auto-detect first .tex file in directory
                fallback_tex = None
                for p in sorted(source_dir.glob("*.tex")):
                    fallback_tex = p
                    break

                if fallback_tex is None:
                    return {"success": False, "error": f"Main file not found and no .tex files present in project: {main_file}"}

                logger.warning(
                    f"Requested main file '{main_file}' not found. Falling back to '{fallback_tex.name}'."
                )

                # Update main_file variables to fallback
                main_file = fallback_tex.name
                main_file_path = fallback_tex

            # Create compilation directory
            compilation_dir = repo_path / "compilations" / compilation_id
            compilation_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy source files to compilation directory
            shutil.copytree(source_dir, compilation_dir / "source", dirs_exist_ok=True)
            
            # Store compilation metadata
            compilation_metadata = {
                "compilation_id": compilation_id,
                "project_id": project_id_str,
                "latex_id": latex_id,
                "latex_name": latex_name,
                "main_file": main_file,
                "output_format": output_format,
                "engine": engine,
                "compiled_by": str(compiled_by) if compiled_by else None,
                "status": "started",
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "errors": [],
                "warnings": [],
                "output_files": []
            }
            
            # Save metadata
            metadata_file = compilation_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(compilation_metadata, f, indent=2)
            
            # Start compilation in background
            asyncio.create_task(self._run_latex_compilation(compilation_dir, compilation_metadata))
            
            logger.info(f"Started LaTeX compilation {compilation_id} for project {project_id_str}")
            
            return {
                "success": True,
                "compilation_id": compilation_id,
                "status": "started",
                "metadata": compilation_metadata
            }
            
        except Exception as e:
            logger.error(f"Error starting LaTeX compilation: {str(e)}")
            return {"success": False, "error": str(e)}

    @handle_service_errors("LaTeX compilation status")
    async def get_compilation_status(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        compilation_id: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get LaTeX compilation status and results.
        
        Args:
            project_id: Project UUID
            latex_id: LaTeX project identifier
            compilation_id: Compilation identifier
            user_id: User requesting status
            
        Returns:
            Dict with compilation status and results
        """
        try:
            # Convert project_id to UUID and string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Get git repository
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": False, "error": "Git repository not found"}
            
            # Check compilation directory
            repo_path = Path(git_repo.repo_path)
            compilation_dir = repo_path / "compilations" / compilation_id
            metadata_file = compilation_dir / "metadata.json"
            
            if not metadata_file.exists():
                return {"success": False, "error": "Compilation not found"}
            
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check for output files
            output_dir = compilation_dir / "output"
            if output_dir.exists():
                output_files = []
                for file_path in output_dir.glob("*"):
                    if file_path.is_file():
                        output_files.append({
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "path": str(file_path.relative_to(compilation_dir))
                        })
                metadata["output_files"] = output_files
            
            return {
                "success": True,
                "compilation": metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting compilation status: {str(e)}")
            return {"success": False, "error": str(e)}

    @handle_service_errors("LaTeX compiled file retrieval")
    async def get_compiled_file(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        compilation_id: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get compiled LaTeX file for download.
        
        Args:
            project_id: Project UUID
            latex_id: LaTeX project identifier
            compilation_id: Compilation identifier
            user_id: User requesting file
            
        Returns:
            Dict with file path and metadata
        """
        try:
            # Convert project_id to UUID and string
            project_uuid = uuid.UUID(project_id) if isinstance(project_id, str) else project_id
            project_id_str = str(project_uuid)
            
            # Get git repository
            repo_result = await self.session.execute(
                select(GitRepository).where(GitRepository.project_id == project_uuid)
            )
            git_repo = repo_result.scalar_one_or_none()
            
            if not git_repo:
                return {"success": False, "error": "Git repository not found"}
            
            # Check compilation directory
            repo_path = Path(git_repo.repo_path)
            compilation_dir = repo_path / "compilations" / compilation_id
            metadata_file = compilation_dir / "metadata.json"
            
            if not metadata_file.exists():
                return {"success": False, "error": "Compilation not found"}
            
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if compilation completed successfully
            if metadata.get("status") != "completed":
                return {"success": False, "error": "Compilation not completed or failed"}
            
            # Look for PDF file in output directory
            output_dir = compilation_dir / "output"
            if not output_dir.exists():
                return {"success": False, "error": "Output directory not found"}
            
            # Find PDF files
            pdf_files = list(output_dir.glob("*.pdf"))
            if not pdf_files:
                return {"success": False, "error": "No PDF file found"}
            
            # Use the first PDF file (usually main.pdf)
            pdf_file = pdf_files[0]
            
            if not pdf_file.exists():
                return {"success": False, "error": "PDF file not found"}
            
            # Extract latex name for filename
            latex_name = latex_id.split(f"{project_id_str}_")[-1]
            filename = f"{latex_name}_{compilation_id[:8]}.pdf"
            
            return {
                "success": True,
                "file_path": str(pdf_file),
                "filename": filename,
                "size": pdf_file.stat().st_size,
                "compilation_id": compilation_id
            }
            
        except Exception as e:
            logger.error(f"Error getting compiled file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _run_latex_compilation(self, compilation_dir: Path, metadata: Dict[str, Any]) -> None:
        """
        Run LaTeX compilation in background.
        
        Args:
            compilation_dir: Directory containing compilation files
            metadata: Compilation metadata
        """
        try:
            source_dir = compilation_dir / "source"
            output_dir = compilation_dir / "output"
            output_dir.mkdir(exist_ok=True)
            
            main_file = metadata["main_file"]
            engine = metadata["engine"]
            
            # Run LaTeX compilation
            cmd = [
                engine,
                "-interaction=nonstopmode",
                "-output-directory=" + str(output_dir),
                main_file
            ]
            
            # Update status to running
            metadata["status"] = "running"
            metadata["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated metadata
            metadata_file = compilation_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Execute compilation
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(source_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Update metadata with results
            metadata["completed_at"] = datetime.utcnow().isoformat()
            
            if process.returncode == 0:
                metadata["status"] = "completed"
                logger.info(f"LaTeX compilation {metadata['compilation_id']} completed successfully")
            else:
                metadata["status"] = "failed"
                error_output = stderr.decode() if stderr else stdout.decode()
                metadata["errors"] = [error_output]
                logger.error(f"LaTeX compilation {metadata['compilation_id']} failed: {error_output}")
            
            # Save final metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            # Update metadata with error
            metadata["status"] = "failed"
            metadata["completed_at"] = datetime.utcnow().isoformat()
            metadata["errors"] = [str(e)]
            
            metadata_file = compilation_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.error(f"LaTeX compilation {metadata['compilation_id']} failed with exception: {str(e)}")

    # ------------------------------------------------------------------
    # Compilation monitoring helpers (used by API background task)
    # ------------------------------------------------------------------

    async def check_compilation_progress(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        compilation_id: str,
    ) -> Dict[str, Any]:
        """Return current status for a running/finished compilation.

        This is a *best-effort* helper so that API endpoints don’t explode if the
        compilation directory/metadata is missing. If metadata cannot be found
        we assume the compilation has failed.
        """
        try:
            repo_base = Path(self._get_repo_path(project_id))
            meta_file = repo_base / "compilations" / compilation_id / "metadata.json"
            if not meta_file.exists():
                return {"status": "failed", "reason": "metadata_not_found"}

            data = json.loads(meta_file.read_text())
            return {"status": data.get("status", "unknown"), "metadata": data}
        except Exception as exc:
            logger.error(f"check_compilation_progress error: {exc}")
            return {"status": "failed", "reason": str(exc)}

    async def mark_compilation_timeout(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        compilation_id: str,
    ) -> None:
        await self._update_compilation_status(project_id, compilation_id, "timeout")

    async def mark_compilation_failed(
        self,
        project_id: uuid.UUID,
        latex_id: str,
        compilation_id: str,
        error: str,
    ) -> None:
        await self._update_compilation_status(project_id, compilation_id, "failed", error)

    # ------------------------- internal helpers -------------------------

    def _get_repo_path(self, project_id: uuid.UUID) -> str:
        """Return repository path for given project from database (sync)."""
        # For helper methods we do a quick synchronous lookup; if it fails we
        # fall back to standard repositories directory layout.
        default_base = Path("/home/yashwardhan/codes/ResXiv_V2/backend/repositories")
        try:
            result = self.session.sync_session.execute(
                select(GitRepository).where(GitRepository.project_id == project_id)
            )
            repo = result.scalar_one_or_none()
            if repo:
                return repo.repo_path
        except Exception:
            pass
        # Fallback to conventional name
        return str(default_base / f"sample_project_{str(project_id)[:8]}")

    async def _update_compilation_status(
        self,
        project_id: uuid.UUID,
        compilation_id: str,
        new_status: str,
        error: str | None = None,
    ) -> None:
        try:
            repo_base = Path(self._get_repo_path(project_id))
            meta_file = repo_base / "compilations" / compilation_id / "metadata.json"
            if not meta_file.exists():
                return
            meta = json.loads(meta_file.read_text())
            meta["status"] = new_status
            if error:
                meta.setdefault("errors", []).append(error)
            meta["completed_at"] = datetime.utcnow().isoformat()
            meta_file.write_text(json.dumps(meta, indent=2))
        except Exception as exc:
            logger.error(f"Failed to update compilation status: {exc}")

    async def _run_git_command(self, cmd: list, cwd: str) -> str:
        """
        Run a Git command asynchronously
        
        Args:
            cmd: Git command as list
            cwd: Working directory
            
        Returns:
            Command output as string
            
        Raises:
            ServiceError: If command fails
        """
        full_cmd = ["git"] + cmd
        
        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Git command failed"
                logger.error(f"Git command failed: {' '.join(full_cmd)} in {cwd}")
                logger.error(f"Exit code: {process.returncode}")
                logger.error(f"stderr: {error_msg}")
                logger.error(f"stdout: {stdout.decode() if stdout else 'None'}")
                raise ServiceError(
                    f"Git command '{' '.join(cmd)}' failed: {error_msg}",
                    ErrorCodes.EXTERNAL_SERVICE_ERROR,
                    500
                )
            
            return stdout.decode()
            
        except FileNotFoundError:
            raise ServiceError(
                "Git is not installed or not found in PATH",
                ErrorCodes.EXTERNAL_SERVICE_ERROR,
                500
            )
        except Exception as e:
            raise ServiceError(
                f"Git command execution failed: {str(e)}",
                ErrorCodes.EXTERNAL_SERVICE_ERROR,
                500
            ) 