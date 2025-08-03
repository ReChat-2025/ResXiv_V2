"""
BibTeX Parser Service - Production Grade
========================================

High-performance BibTeX parsing with validation and error handling.
Follows SOLID principles with clean separation of concerns.
"""

import bibtexparser
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedPaper:
    """Immutable paper representation from BibTeX entry."""
    title: str
    authors: List[str]
    year: str
    booktitle: str
    journal: str
    doi: str
    eprint: str
    entry_type: str
    citation_key: str
    raw_entry: Dict[str, Any]

    def __post_init__(self):
        """Validate and clean fields after initialization."""
        # Clean authors list
        if isinstance(self.authors, str):
            self.authors = [a.strip() for a in self.authors.split(' and ') if a.strip()]
        elif not isinstance(self.authors, list):
            self.authors = []
        
        # Ensure all string fields are strings
        for field in ['title', 'year', 'booktitle', 'journal', 'doi', 'eprint', 'entry_type', 'citation_key']:
            if not isinstance(getattr(self, field), str):
                setattr(self, field, str(getattr(self, field) or ''))


class BibParser:
    """
    Production-grade BibTeX parser with comprehensive error handling.
    
    Designed for high throughput with minimal memory footprint.
    Validates entries and provides detailed error reporting.
    """
    
    @staticmethod
    def parse_content(bib_content: str) -> List[ParsedPaper]:
        """
        Parse BibTeX content into validated ParsedPaper objects.
        
        Args:
            bib_content: Raw BibTeX content string
            
        Returns:
            List of ParsedPaper objects
            
        Raises:
            ValueError: If content is malformed or empty
        """
        if not bib_content or not bib_content.strip():
            return []
            
        try:
            # Use bibtexparser with default configuration for robustness
            bib_database = bibtexparser.loads(bib_content)
            
            if not bib_database.entries:
                logger.warning("No BibTeX entries found in content")
                return []
            
            papers = []
            for entry in bib_database.entries:
                try:
                    paper = BibParser._create_paper_from_entry(entry)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Skipping malformed entry {entry.get('ID', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(papers)} papers from {len(bib_database.entries)} entries")
            return papers
            
        except Exception as e:
            logger.error(f"BibTeX parsing failed: {e}")
            raise ValueError(f"Failed to parse BibTeX content: {e}")
    
    @staticmethod
    def parse_file(file_path: Path) -> List[ParsedPaper]:
        """
        Parse BibTeX file into validated ParsedPaper objects.
        
        Args:
            file_path: Path to BibTeX file
            
        Returns:
            List of ParsedPaper objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file content is malformed
        """
        if not file_path.exists():
            raise FileNotFoundError(f"BibTeX file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return BibParser.parse_content(content)
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            return BibParser.parse_content(content)
    
    @staticmethod
    def _create_paper_from_entry(entry: Dict[str, Any]) -> ParsedPaper:
        """Create ParsedPaper from bibtexparser entry with validation."""
        # Extract and clean authors
        authors_raw = entry.get('author', '')
        if authors_raw:
            authors = [a.strip() for a in authors_raw.split(' and ') if a.strip()]
        else:
            authors = []
        
        return ParsedPaper(
            title=entry.get('title', '').strip(),
            authors=authors,
            year=entry.get('year', '').strip(),
            booktitle=entry.get('booktitle', '').strip(),
            journal=entry.get('journal', '').strip(),
            doi=entry.get('doi', '').strip(),
            eprint=entry.get('eprint', '').strip(),
            entry_type=entry.get('ENTRYTYPE', 'misc').strip(),
            citation_key=entry.get('ID', '').strip(),
            raw_entry=entry
        )
    
    @staticmethod
    def validate_entry(paper: ParsedPaper) -> bool:
        """
        Validate that a ParsedPaper has minimum required fields.
        
        Args:
            paper: ParsedPaper to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Must have title and at least one of: authors, year, journal, booktitle
        has_title = bool(paper.title and paper.title.strip())
        has_metadata = any([
            paper.authors,
            paper.year and paper.year.strip(),
            paper.journal and paper.journal.strip(),
            paper.booktitle and paper.booktitle.strip()
        ])
        
        return has_title and has_metadata 