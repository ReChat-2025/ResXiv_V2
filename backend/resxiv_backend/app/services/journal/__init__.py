"""
Journal Services Package - L6 Engineering Standards

Modular journal service system split from bloated monolithic file.
Clean separation following Single Responsibility Principle.
"""

from .journal_crud_service import JournalCrudService
from .journal_collaboration_service import JournalCollaborationService

__all__ = [
    "JournalCrudService",
    "JournalCollaborationService"
] 