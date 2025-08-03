"""
Git Repository Service - L6 Engineering Standards
Production-grade Git repository management with proper filesystem operations.
Single Responsibility: Git repository lifecycle and file operations.
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import GitRepository, Branch
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GitRepositoryService:
    """
    Production Git repository service for proper version control.
    Single Responsibility: Git repository and branch operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = BranchRepository(session)
        
        # Git repositories base directory - use relative path within project
        default_git_dir = Path(__file__).parent.parent.parent.parent.parent / "repositories"
        self.git_base_dir = Path(os.getenv("RESXIV_GIT_DIR", str(default_git_dir)))
        self.git_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Git repositories will be stored in: {self.git_base_dir.absolute()}")
    
    @handle_service_errors("initialize git repository")
    async def initialize_project_repository(
        self,
        project_id: uuid.UUID,
        project_name: str,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Initialize a real Git repository for a project.
        
        Args:
            project_id: Project UUID
            project_name: Project name for directory
            created_by: User creating the repository
            
        Returns:
            Repository initialization result
        """
        # Check if repository already exists
        existing_repo = await self.repository.get_project_git_repository(project_id)
        if existing_repo:
            # Repository already exists - this is normal, return success
            logger.info(f"Git repository already exists for project {project_id} at {existing_repo.repo_path}")
            return {
                "success": True,
                "repo_path": existing_repo.repo_path,
                "main_branch_id": str(existing_repo.default_branch_id) if existing_repo.default_branch_id else None,
                "message": "Git repository already initialized"
            }
        
        # Create repository directory
        safe_name = self._sanitize_name(project_name)
        repo_path = self.git_base_dir / f"{safe_name}_{str(project_id)[:8]}"
        
        try:
            # Create the repository directory first
            repo_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created repository directory: {repo_path}")
            
            # Initialize Git repository in the created directory
            await self._run_git_command(["init"], str(repo_path))
            logger.info(f"Git repository initialized in: {repo_path}")
            
            # Set up initial commit
            await self._create_initial_structure(repo_path, created_by)
            
            # Create database record
            git_repo = await self.repository.create_git_repository(
                project_id=project_id,
                repo_path=str(repo_path)
            )
            
            # Create main branch record
            main_branch = await self._create_main_branch(project_id, created_by, git_repo)
            
            # Update repository with default branch
            git_repo.default_branch_id = main_branch.id
            git_repo.initialized = True
            
            await self.session.commit()
            
            return {
                "success": True,
                "repo_path": str(repo_path),
                "main_branch_id": str(main_branch.id),
                "message": "Git repository initialized successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            # Clean up directory if creation failed
            if repo_path.exists():
                import shutil
                shutil.rmtree(repo_path, ignore_errors=True)
            raise ServiceError(
                f"Failed to initialize repository: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("create git branch")
    async def create_git_branch(
        self,
        project_id: uuid.UUID,
        branch_name: str,
        source_branch_name: Optional[str] = None,
        created_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Create a real Git branch in the repository.
        
        Args:
            project_id: Project UUID
            branch_name: New branch name
            source_branch_name: Source branch (defaults to main)
            created_by: User creating the branch
            
        Returns:
            Branch creation result
        """
        # Get repository
        git_repo = await self.repository.get_project_git_repository(project_id)
        if not git_repo or not git_repo.initialized:
            return {
                "success": False,
                "error": "Project repository not initialized"
            }
        
        repo_path = Path(git_repo.repo_path)
        if not repo_path.exists():
            return {
                "success": False,
                "error": "Repository directory not found"
            }
        
        try:
            # Checkout source branch (default to main)
            source_branch = source_branch_name or "main"
            await self._run_git_command(["checkout", source_branch], str(repo_path))
            
            # Create and checkout new branch
            await self._run_git_command(["checkout", "-b", branch_name], str(repo_path))
            
            # Get commit hash
            commit_hash = await self._get_current_commit_hash(repo_path)
            
            return {
                "success": True,
                "branch_name": branch_name,
                "commit_hash": commit_hash,
                "message": f"Branch '{branch_name}' created successfully"
            }
            
        except Exception as e:
            raise ServiceError(
                f"Failed to create Git branch: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("write file to repository")
    async def write_file_to_repository(
        self,
        project_id: uuid.UUID,
        branch_name: str,
        file_path: str,
        content: str,
        commit_message: Optional[str] = None,
        author_name: str = "ResXiv User",
        author_email: str = "user@resxiv.com"
    ) -> Dict[str, Any]:
        """
        Write file to Git repository and commit changes.
        
        Args:
            project_id: Project UUID
            branch_name: Target branch
            file_path: Relative file path (e.g., "main.tex", "sections/intro.tex")
            content: File content
            commit_message: Commit message
            author_name: Git author name
            author_email: Git author email
            
        Returns:
            File write result with commit hash
        """
        # Get repository
        git_repo = await self.repository.get_project_git_repository(project_id)
        if not git_repo:
            return {
                "success": False,
                "error": "Repository not found"
            }
        
        repo_path = Path(git_repo.repo_path)
        relative_path = file_path.lstrip("/")
        full_file_path = repo_path / relative_path
        
        try:
            # Validate Git repository state
            logger.info(f"Validating Git repository state for project {project_id}")
            try:
                # Check if this is a valid Git repository
                await self._run_git_command(["status", "--porcelain"], str(repo_path))
                logger.info("Git repository status check passed")
            except ServiceError as e:
                logger.error(f"Git repository validation failed: {str(e)}")
                raise ServiceError(
                    f"Git repository is in an invalid state: {str(e)}",
                    ErrorCodes.VALIDATION_ERROR
                )
            
            # Clean up any problematic untracked files that might interfere with staging
            await self._cleanup_repository_state(repo_path)
            
            # Checkout target branch
            logger.info(f"Checking out branch: {branch_name}")
            await self._run_git_command(["checkout", branch_name], str(repo_path))
            
            # Configure Git user for this repository (needed for commits)
            logger.info(f"Configuring Git user: {author_name} <{author_email}>")
            await self._run_git_command(["config", "user.name", author_name], str(repo_path))
            await self._run_git_command(["config", "user.email", author_email], str(repo_path))
            
            # Ensure directory exists - handle conflicts with existing files
            logger.info(f"Creating directory structure for: {full_file_path}")
            try:
                full_file_path.parent.mkdir(parents=True, exist_ok=True)
            except FileExistsError as e:
                # Check if a file (not directory) exists with the same name as the directory we're trying to create
                conflicting_path = None
                for parent in full_file_path.parents:
                    if parent.exists() and not parent.is_dir():
                        conflicting_path = parent
                        break
                
                if conflicting_path:
                    raise ServiceError(
                        f"Cannot create directory '{conflicting_path.relative_to(repo_path)}' because a file with the same name already exists. "
                        f"Please choose a different path or rename the existing file.",
                        ErrorCodes.VALIDATION_ERROR
                    )
                else:
                    # Re-raise if it's a different type of FileExistsError
                    raise ServiceError(
                        f"Directory creation failed: {str(e)}",
                        ErrorCodes.UPDATE_ERROR
                    )
            
            # For LaTeX files, provide minimal template if content is empty
            actual_content = content
            if not content.strip():
                if file_path.endswith('.tex'):
                    # Minimal LaTeX template for empty files
                    actual_content = "% Empty LaTeX file\n% Add your content here\n"
                else:
                    # For other files, add a comment to make them non-empty
                    actual_content = f"% Empty {file_path.split('.')[-1] if '.' in file_path else 'file'}\n"
            
            # Write file content
            logger.info(f"Writing file: {full_file_path}")
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(actual_content)
            
            # Stage the file with robust retry logic
            logger.info(f"Staging file: {relative_path}")
            
            # Initial staging attempt
            await self._run_git_command(["add", relative_path], str(repo_path))
            
            # Verify file is staged with multiple attempts
            max_staging_attempts = 3
            staging_successful = False
            
            for attempt in range(max_staging_attempts):
                try:
                    staged_files = await self._run_git_command(["diff", "--cached", "--name-only"], str(repo_path))
                    if relative_path in staged_files:
                        staging_successful = True
                        logger.info(f"File {relative_path} successfully staged on attempt {attempt + 1}")
                        break
                    else:
                        logger.warning(f"File {relative_path} not found in staged files on attempt {attempt + 1}")
                        logger.info(f"Currently staged files: {staged_files}")
                        
                        if attempt < max_staging_attempts - 1:
                            # Try different staging approaches
                            if attempt == 0:
                                # Try staging with full path
                                await self._run_git_command(["add", str(full_file_path)], str(repo_path))
                            elif attempt == 1:
                                # Try staging with force flag
                                await self._run_git_command(["add", "-f", relative_path], str(repo_path))
                            
                            # Small delay before retry
                            await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error verifying staging on attempt {attempt + 1}: {str(e)}")
                    if attempt < max_staging_attempts - 1:
                        await asyncio.sleep(0.1)
            
            if not staging_successful:
                # Last resort: check if file exists and try one more time
                if full_file_path.exists():
                    logger.info("File exists but not staged. Attempting final staging with status check.")
                    
                    # Check repository status
                    status_output = await self._run_git_command(["status", "--porcelain"], str(repo_path))
                    logger.info(f"Repository status: {status_output}")
                    
                    # Try staging all changes to this specific file
                    await self._run_git_command(["add", "-A", relative_path], str(repo_path))
                    
                    # Final verification
                    final_staged = await self._run_git_command(["diff", "--cached", "--name-only"], str(repo_path))
                    if relative_path not in final_staged:
                        raise ServiceError(
                            f"Failed to stage file {relative_path} after multiple attempts. "
                            f"Repository may have conflicting states. Status: {status_output}",
                            ErrorCodes.UPDATE_ERROR
                        )
                else:
                    raise ServiceError(
                        f"File {full_file_path} was not created properly",
                        ErrorCodes.UPDATE_ERROR
                    )
            
            # Create commit
            commit_msg = commit_message or f"Update {relative_path}"
            logger.info(f"Creating commit with message: {commit_msg}")
            await self._run_git_command([
                "commit", 
                "-m", commit_msg,
                "--author", f"{author_name} <{author_email}>"
            ], str(repo_path))
            
            # Get new commit hash
            commit_hash = await self._get_current_commit_hash(repo_path)
            logger.info(f"File committed successfully with hash: {commit_hash}")
            
            return {
                "success": True,
                "file_path": relative_path,
                "commit_hash": commit_hash,
                "message": f"File {file_path} committed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to write file to repository: {str(e)}")
            raise ServiceError(
                f"Failed to write file to repository: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("read file from repository")
    async def read_file_from_repository(
        self,
        project_id: uuid.UUID,
        branch_name: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Read file content from Git repository.
        
        Args:
            project_id: Project UUID
            branch_name: Target branch
            file_path: Relative file path
            
        Returns:
            File content and metadata
        """
        # Get repository
        git_repo = await self.repository.get_project_git_repository(project_id)
        if not git_repo:
            return {
                "success": False,
                "error": "Repository not found"
            }
        
        repo_path = Path(git_repo.repo_path)
        full_file_path = repo_path / file_path.lstrip("/")
        
        try:
            # Checkout target branch
            await self._run_git_command(["checkout", branch_name], str(repo_path))
            
            if not full_file_path.exists():
                return {
                    "success": False,
                    "error": f"File {file_path} not found"
                }
            
            # Read file content
            with open(full_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file stats
            file_stats = full_file_path.stat()
            
            return {
                "success": True,
                "content": content,
                "file_path": file_path,
                "file_size": file_stats.st_size,
                "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            }
            
        except Exception as e:
            raise ServiceError(
                f"Failed to read file from repository: {str(e)}",
                ErrorCodes.NOT_FOUND_ERROR
            )
    
    @handle_service_errors("list repository files")
    async def list_repository_files(
        self,
        project_id: uuid.UUID,
        branch_name: str
    ) -> Dict[str, Any]:
        """
        List all files in repository branch.
        
        Args:
            project_id: Project UUID
            branch_name: Target branch
            
        Returns:
            List of files with metadata
        """
        # Get repository
        git_repo = await self.repository.get_project_git_repository(project_id)
        if not git_repo:
            return {
                "success": False,
                "error": "Repository not found"
            }
        
        repo_path = Path(git_repo.repo_path)
        
        try:
            # Checkout target branch
            await self._run_git_command(["checkout", branch_name], str(repo_path))
            
            # List tracked files
            result = await self._run_git_command(["ls-files"], str(repo_path))
            file_list = result.strip().split('\n') if result.strip() else []
            
            files = []
            for file_path in file_list:
                if file_path:  # Skip empty lines
                    full_path = repo_path / file_path
                    if full_path.exists():
                        file_stats = full_path.stat()
                        files.append({
                            "file_path": f"/{file_path}",
                            "file_name": Path(file_path).name,
                            "file_size": file_stats.st_size,
                            "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                        })
            
            return {
                "success": True,
                "files": files,
                "total_count": len(files),
                "branch_name": branch_name
            }
            
        except Exception as e:
            raise ServiceError(
                f"Failed to list repository files: {str(e)}",
                ErrorCodes.SEARCH_ERROR
            )
    
    # Private helper methods
    
    async def _run_git_command(
        self,
        command: List[str],
        cwd: str,
        create_dir: bool = False
    ) -> str:
        """Run Git command with proper error handling"""
        if create_dir:
            Path(cwd).mkdir(parents=True, exist_ok=True)
            
        # Enhanced logging for debugging
        logger.info(f"Running Git command: git {' '.join(command)} in directory: {cwd}")
        
        process = await asyncio.create_subprocess_exec(
            "git", *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            # Decode output for better error reporting
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            logger.error(f"Git command failed:")
            logger.error(f"  Command: git {' '.join(command)}")
            logger.error(f"  Working directory: {cwd}")
            logger.error(f"  Exit code: {process.returncode}")
            logger.error(f"  stdout: {stdout_text}")
            logger.error(f"  stderr: {stderr_text}")
            
            # Check for common Git issues
            if "not a git repository" in stderr_text.lower():
                error_msg = f"Not a Git repository: {cwd}"
            elif "author identity unknown" in stderr_text.lower() or "user.name" in stderr_text.lower():
                error_msg = "Git user configuration missing"
            elif "permission denied" in stderr_text.lower():
                error_msg = f"Permission denied in Git repository: {cwd}"
            elif stderr_text:
                error_msg = stderr_text
            elif stdout_text:
                error_msg = stdout_text
            else:
                error_msg = f"Unknown Git error (exit code: {process.returncode})"
            
            raise ServiceError(
                f"Git command failed: {' '.join(command)} - {error_msg}",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
        
        return stdout.decode().strip()
    
    async def _create_initial_structure(self, repo_path: Path, created_by: uuid.UUID):
        """Create initial repository structure"""
        # Create initial .gitignore
        gitignore_content = """
# LaTeX auxiliary files
*.aux
*.log
*.out
*.toc
*.fdb_latexmk
*.fls
*.synctex.gz

# OS files
.DS_Store
Thumbs.db
"""
        with open(repo_path / ".gitignore", 'w') as f:
            f.write(gitignore_content.strip())
        
        # Create README.md
        readme_content = f"""# ResXiv Project

This is a ResXiv project repository for collaborative LaTeX document editing.

## Getting Started

This repository uses Git for version control and branch management.
Each branch represents a different version or collaboration track of your documents.

## Branches

- `main` - The main development branch

## Files

Add your LaTeX files using the ResXiv interface for proper collaboration and version control.
"""
        with open(repo_path / "README.md", 'w') as f:
            f.write(readme_content.strip())
        
        # Set the default branch to 'main' before making initial commit
        await self._run_git_command(["config", "init.defaultBranch", "main"], str(repo_path))
        
        # Configure Git user for initial commit
        await self._run_git_command(["config", "user.name", "ResXiv System"], str(repo_path))
        await self._run_git_command(["config", "user.email", "system@resxiv.com"], str(repo_path))
        
        # Add and commit initial files
        await self._run_git_command(["add", "."], str(repo_path))
        await self._run_git_command([
            "commit", "-m", "Initial commit - ResXiv project setup"
        ], str(repo_path))
        
        # Ensure we're on the main branch (rename master to main if needed)
        try:
            # Check current branch
            current_branch = await self._run_git_command(["branch", "--show-current"], str(repo_path))
            if current_branch.strip() == "master":
                # Rename master to main
                await self._run_git_command(["branch", "-m", "master", "main"], str(repo_path))
        except:
            # If any command fails, continue - the branch will be main by default
            pass
    
    async def _create_main_branch(
        self,
        project_id: uuid.UUID,
        created_by: uuid.UUID,
        git_repo: GitRepository
    ) -> Branch:
        """Create main branch database record with permissions"""
        from app.schemas.branch import Branch
        
        main_branch = Branch(
            project_id=project_id,
            name="main",
            description="Main development branch",
            is_default=True,
            created_by=created_by,
            head_commit_hash=await self._get_current_commit_hash(Path(git_repo.repo_path))
        )
        
        self.session.add(main_branch)
        await self.session.flush()  # Get ID
        
        # Create permissions for the project owner (full access)
        await self.repository.add_branch_permission(
            branch_id=main_branch.id,
            user_id=created_by,
            can_read=True,
            can_write=True,
            can_admin=True,
            granted_by=created_by
        )
        
        logger.info(f"✅ Main branch '{main_branch.name}' created with full permissions for user {created_by}")
        return main_branch
    
    async def _cleanup_repository_state(self, repo_path: Path) -> None:
        """Clean up repository state to prevent staging issues"""
        try:
            # Check for untracked files that might interfere with operations
            status_output = await self._run_git_command(["status", "--porcelain"], str(repo_path))
            
            if status_output:
                logger.info(f"Repository has untracked files: {status_output}")
                
                # Check for temporary directories that can be safely ignored
                lines = status_output.strip().split('\n')
                for line in lines:
                    if line.startswith('??'):  # Untracked files
                        file_path = line[3:].strip()  # Remove '?? ' prefix
                        
                        # Handle problematic temporary directories
                        if file_path.startswith('compilations/'):
                            temp_dir = repo_path / file_path.split('/')[0]
                            if temp_dir.exists() and temp_dir.is_dir():
                                logger.info(f"Adding temporary directory to gitignore: {file_path.split('/')[0]}")
                                
                                # Add to .gitignore if not already there
                                gitignore_path = repo_path / '.gitignore'
                                ignore_pattern = f"{file_path.split('/')[0]}/\n"
                                
                                if gitignore_path.exists():
                                    with open(gitignore_path, 'r', encoding='utf-8') as f:
                                        gitignore_content = f.read()
                                    
                                    if ignore_pattern.strip() not in gitignore_content:
                                        with open(gitignore_path, 'a', encoding='utf-8') as f:
                                            f.write(ignore_pattern)
                                        logger.info(f"Added {file_path.split('/')[0]}/ to .gitignore")
                                else:
                                    # Create .gitignore
                                    with open(gitignore_path, 'w', encoding='utf-8') as f:
                                        f.write(f"# Automatically generated\n{ignore_pattern}")
                                    logger.info(f"Created .gitignore with {file_path.split('/')[0]}/")
                
        except Exception as e:
            # Don't fail the entire operation if cleanup fails
            logger.warning(f"Repository cleanup warning (non-critical): {str(e)}")
    
    async def _get_current_commit_hash(self, repo_path: Path) -> str:
        """Get current commit hash"""
        try:
            return await self._run_git_command(["rev-parse", "HEAD"], str(repo_path))
        except:
            return ""
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for filesystem"""
        import re
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower()) 