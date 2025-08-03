"""
Paper Storage Service - L6 Engineering Standards
Focused on file upload, storage, and validation operations.
"""

import os
import re
import hashlib
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.paper_repository import PaperRepository

logger = logging.getLogger(__name__)


class PaperStorageService:
    """
    Storage service for paper file operations.
    Single Responsibility: File upload, storage, and validation.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaperRepository(session)
        
        # File processing configuration
        self.base_dir = Path(os.getenv("RESXIV_DATA_DIR", "/ResXiv_V2"))
        self.papers_dir = self.base_dir / "papers"
        self.bib_dir = self.base_dir / "bib"
        self.xml_dir = self.base_dir / "xml"
        self._ensure_directories()
        
        # Processing settings
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_extensions = {'.pdf', '.tex', '.bib'}
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        for directory in [self.papers_dir, self.bib_dir, self.xml_dir]:
            directory.mkdir(exist_ok=True, parents=True)
    
    @handle_service_errors("validate uploaded file")
    async def validate_upload(self, file: UploadFile) -> Dict[str, Any]:
        """
        Validate uploaded file for paper submission.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Validation result
        """
        # Check file size
        if file.size and file.size > self.max_file_size:
            raise ServiceError(
                f"File size {file.size} exceeds maximum allowed size {self.max_file_size}",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise ServiceError(
                f"File type {file_extension} not allowed. Allowed types: {', '.join(self.allowed_extensions)}",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Check filename
        if not file.filename or len(file.filename) > 255:
            raise ServiceError(
                "Invalid filename",
                ErrorCodes.VALIDATION_ERROR
            )
        
        return {
            "success": True,
            "file_info": {
                "filename": file.filename,
                "size": file.size,
                "extension": file_extension,
                "content_type": file.content_type
            }
        }
    
    def generate_safe_title(self, title: str) -> str:
        """Generate a safe filename from paper title"""
        safe_title = re.sub(r'[^\w\s-]', '', title.strip())
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        safe_title = safe_title.lower().strip('-')
        
        if len(safe_title) > 100:
            safe_title = safe_title[:100].rsplit('-', 1)[0]
        
        return safe_title or "untitled"
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def generate_file_hash(self, file_obj) -> str:
        """Generate MD5 hash from file object content."""
        try:
            # Handle UploadFile objects
            if hasattr(file_obj, 'file'):
                actual_file = file_obj.file
            else:
                actual_file = file_obj
                
            # Save current position
            current_pos = actual_file.tell()
            
            # Go to start and read content
            actual_file.seek(0)
            content = actual_file.read()
            
            # Reset position
            actual_file.seek(current_pos)
            
            # Generate hash
            hash_md5 = hashlib.md5()
            hash_md5.update(content)
            return hash_md5.hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            # Reset position in case of error
            try:
                file_obj.seek(current_pos)
            except:
                pass
            raise
    
    @handle_service_errors("store uploaded file")
    async def store_file(
        self,
        file: UploadFile,
        paper_id: str,
        title: str
    ) -> Dict[str, Any]:
        """
        Store uploaded file to the file system.
        
        Args:
            file: Uploaded file object
            paper_id: Paper UUID
            title: Paper title for filename generation
            
        Returns:
            Storage result with file paths
        """
        # Generate safe filename
        safe_title = self.generate_safe_title(title)
        file_extension = Path(file.filename).suffix.lower()
        filename = f"{safe_title}-{paper_id}{file_extension}"
        
        # Determine storage directory based on file type
        if file_extension == '.pdf':
            storage_dir = self.papers_dir
        elif file_extension == '.bib':
            storage_dir = self.bib_dir
        else:
            storage_dir = self.papers_dir
        
        file_path = storage_dir / filename
        
        try:
            # Store file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Calculate checksum of stored file  
            checksum = self.calculate_file_checksum(file_path)
            
            # Get file stats
            file_stats = file_path.stat()
            
            # Persist file metadata back to DB (path/size/mime/checksum)
            relative_path = str(file_path.relative_to(self.base_dir))
            update_payload = {
                "file_size": file_stats.st_size,
                "mime_type": file.content_type,
                "checksum": checksum,
            }
            if file_extension == ".pdf":
                update_payload["pdf_path"] = relative_path
            elif file_extension == ".bib":
                update_payload["bib_path"] = relative_path
            else:
                update_payload["pdf_path"] = relative_path  # default

            await self.repository.update_paper(paper_id, update_payload)
            await self.session.commit()

            # Close the file handle
            try:
                open(file_path, 'rb').close()
            except:
                pass

            return {
                "success": True,
                "file_info": {
                    "filename": filename,
                    "original_filename": file.filename,
                    "relative_path": relative_path,
                    "size": file_stats.st_size,
                    "checksum": checksum,
                    "stored_at": datetime.fromtimestamp(file_stats.st_mtime)
                }
            }
            
        except Exception as e:
            # Clean up partial file if error occurred
            if file_path.exists():
                file_path.unlink()
            raise ServiceError(
                f"Failed to store file: {str(e)}",
                ErrorCodes.STORAGE_ERROR
            )
    
    @handle_service_errors("retrieve file")
    async def get_file_path(self, paper_id: str) -> Optional[Path]:
        """
        Get the file path for a paper.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            File path if found
        """
        # Get paper from database
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            return None

        relative_path = paper.pdf_path or paper.bib_path
        if not relative_path:
            return None

        file_path = self.base_dir / relative_path
        
        if not file_path.exists():
            logger.warning(f"File not found on disk: {file_path}")
            return None
        
        return file_path
    
    @handle_service_errors("delete file")
    async def delete_file(self, paper_id: str) -> Dict[str, Any]:
        """
        Delete stored file for a paper.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Deletion result
        """
        file_path = await self.get_file_path(paper_id)
        if not file_path:
            return {
                "success": True,
                "message": "File not found or already deleted"
            }
        
        try:
            file_path.unlink()
            return {
                "success": True,
                "message": "File deleted successfully"
            }
        except Exception as e:
            raise ServiceError(
                f"Failed to delete file: {str(e)}",
                ErrorCodes.STORAGE_ERROR
            )
    
    @handle_service_errors("check file integrity")
    async def verify_file_integrity(self, paper_id: str) -> Dict[str, Any]:
        """
        Verify file integrity using checksum.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Integrity check result
        """
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        file_path = await self.get_file_path(paper_id)
        if not file_path:
            raise ServiceError(
                "File not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Calculate current checksum
        current_checksum = self.calculate_file_checksum(file_path)
        
        # Compare with stored checksum
        integrity_valid = (paper.checksum == current_checksum)
        
        return {
            "success": True,
            "integrity_valid": integrity_valid,
            "current_checksum": current_checksum,
            "stored_checksum": paper.checksum,
            "file_path": str(file_path)
        }
    
    @handle_service_errors("get storage statistics")
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics
        """
        stats = {
            "directories": {},
            "total_files": 0,
            "total_size": 0
        }
        
        for directory_name, directory_path in [
            ("papers", self.papers_dir),
            ("bib", self.bib_dir),
            ("xml", self.xml_dir)
        ]:
            if directory_path.exists():
                files = list(directory_path.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                
                stats["directories"][directory_name] = {
                    "path": str(directory_path),
                    "file_count": len(files),
                    "total_size": total_size
                }
                
                stats["total_files"] += len(files)
                stats["total_size"] += total_size
        
        return {
            "success": True,
            "statistics": stats
        } 