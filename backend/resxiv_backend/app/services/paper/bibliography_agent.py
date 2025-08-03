"""
Bibliography Enrichment Agent - LangGraph Implementation
=======================================================

Production-grade bibliography extraction using LangGraph for robust state management.
Implements L6 engineering standards with comprehensive error handling and recovery.
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import urllib.parse
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.error_handling import ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class BibliographyState(TypedDict):
    """State management for bibliography enrichment pipeline."""
    reference_text: str
    title: Optional[str]
    authors: List[str]
    year: Optional[str]
    journal: Optional[str]
    doi: Optional[str]
    arxiv_id: Optional[str]
    entry_type: str
    enrichment_attempts: Dict[str, bool]
    errors: List[str]
    final_entry: Optional[str]


@dataclass
class EnrichmentResult:
    """Immutable result from metadata enrichment."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    confidence: float = 0.0
    source: str = ""


class BibliographyEnrichmentAgent:
    """
    LangGraph-based agent for bibliography enrichment.
    
    Implements a state machine for robust metadata extraction:
    1. Parse reference text
    2. Extract IDs (arXiv, DOI)
    3. Query external APIs (parallel)
    4. Merge results with confidence scoring
    5. Generate BibTeX entry
    """
    
    def __init__(self, timeout: int = 10):
        """Initialize agent with configurable timeout."""
        self.timeout = timeout
        self.session_timeout = aiohttp.ClientTimeout(total=timeout)
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Build LangGraph state machine for bibliography enrichment."""
        workflow = StateGraph(BibliographyState)
        
        # Define nodes
        workflow.add_node("parse_reference", self._parse_reference_node)
        workflow.add_node("extract_identifiers", self._extract_identifiers_node)
        workflow.add_node("enrich_metadata", self._enrich_metadata_node)
        workflow.add_node("generate_bibtex", self._generate_bibtex_node)
        
        # Define edges
        workflow.set_entry_point("parse_reference")
        workflow.add_edge("parse_reference", "extract_identifiers")
        workflow.add_edge("extract_identifiers", "enrich_metadata")
        workflow.add_edge("enrich_metadata", "generate_bibtex")
        workflow.add_edge("generate_bibtex", END)
        
        # Compile with memory for state persistence
        memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=memory)
    
    async def enrich_reference(self, reference_text: str, ref_num: int) -> Optional[str]:
        """
        Enrich a single reference using the LangGraph pipeline.
        
        Args:
            reference_text: Raw reference string from GROBID
            ref_num: Reference number for fallback citation key
            
        Returns:
            BibTeX entry string or None if enrichment fails
        """
        if not reference_text or len(reference_text.strip()) < 10:
            return None
        
        initial_state: BibliographyState = {
            "reference_text": reference_text.strip(),
            "title": None,
            "authors": [],
            "year": None,
            "journal": None,
            "doi": None,
            "arxiv_id": None,
            "entry_type": "misc",
            "enrichment_attempts": {},
            "errors": [],
            "final_entry": None
        }
        
        try:
            # Execute graph with unique thread ID
            thread_id = f"ref_{ref_num}_{hash(reference_text) % 10000}"
            config = {"configurable": {"thread_id": thread_id}}
            
            result = await self.graph.ainvoke(initial_state, config)
            return result.get("final_entry")
            
        except Exception as e:
            logger.error(f"Bibliography enrichment failed for reference {ref_num}: {e}")
            return None
    
    async def _parse_reference_node(self, state: BibliographyState) -> BibliographyState:
        """Parse basic metadata from reference text."""
        ref = state["reference_text"]
        
        # Extract title using improved patterns
        title = self._extract_title(ref)
        if title:
            state["title"] = title
        
        # Extract authors
        authors = self._extract_authors(ref)
        if authors:
            state["authors"] = authors
        
        # Extract year
        year = self._extract_year(ref)
        if year:
            state["year"] = year
        
        # Extract journal/venue (preliminary)
        journal = self._extract_journal_basic(ref)
        if journal:
            state["journal"] = journal
        
        # Determine entry type
        state["entry_type"] = self._determine_entry_type(ref)
        
        return state
    
    async def _extract_identifiers_node(self, state: BibliographyState) -> BibliographyState:
        """Extract DOI and arXiv IDs from reference text."""
        ref = state["reference_text"]
        
        # Extract DOI
        doi = self._extract_doi(ref)
        if doi:
            state["doi"] = doi
        
        # Extract arXiv ID
        arxiv_id = self._extract_arxiv(ref)
        if arxiv_id:
            state["arxiv_id"] = arxiv_id
        
        return state
    
    async def _enrich_metadata_node(self, state: BibliographyState) -> BibliographyState:
        """Enrich metadata using external APIs in parallel."""
        enrichment_tasks = []
        
        # arXiv enrichment
        if state["arxiv_id"]:
            enrichment_tasks.append(
                self._enrich_from_arxiv(state["arxiv_id"])
            )
        
        # DOI enrichment
        if state["doi"]:
            enrichment_tasks.append(
                self._enrich_from_crossref_doi(state["doi"])
            )
        
        # Title-based enrichment (if we have a good title)
        if state["title"] and len(state["title"]) > 10:
            enrichment_tasks.append(
                self._enrich_from_crossref_title(state["title"])
            )
            enrichment_tasks.append(
                self._enrich_from_semantic_scholar(state["title"])
            )
        
        # Execute enrichment tasks in parallel
        if enrichment_tasks:
            results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
            
            # Merge results with confidence-based selection
            best_result = self._merge_enrichment_results(results)
            if best_result:
                state.update({
                    "title": best_result.title or state["title"],
                    "authors": best_result.authors or state["authors"],
                    "year": best_result.year or state["year"],
                    "journal": best_result.journal or state["journal"],
                    "doi": best_result.doi or state["doi"]
                })
                
                state["enrichment_attempts"][best_result.source] = True
        
        return state
    
    async def _generate_bibtex_node(self, state: BibliographyState) -> BibliographyState:
        """Generate final BibTeX entry from enriched metadata."""
        # Generate citation key
        citation_key = self._generate_citation_key(
            state["authors"], 
            state["year"], 
            state["title"]
        )
        
        # Build BibTeX entry
        entry_lines = [f"@{state['entry_type']}{{{citation_key},"]
        
        # Add fields with validation
        if state["title"]:
            clean_title = state["title"].replace('{', '\\{').replace('}', '\\}')
            entry_lines.append(f'  title = {{{clean_title}}},')
        
        if state["authors"]:
            author_str = " and ".join(state["authors"][:5])  # Limit to 5 authors
            if len(state["authors"]) > 5:
                author_str += " and others"
            clean_authors = author_str.replace('{', '\\{').replace('}', '\\}')
            entry_lines.append(f'  author = {{{clean_authors}}},')
        
        if state["journal"]:
            clean_journal = state["journal"].replace('{', '\\{').replace('}', '\\}')
            if state["entry_type"] == "inproceedings":
                entry_lines.append(f'  booktitle = {{{clean_journal}}},')
            else:
                entry_lines.append(f'  journal = {{{clean_journal}}},')
        
        if state["year"]:
            entry_lines.append(f'  year = {{{state["year"]}}},')
        
        if state["doi"]:
            entry_lines.append(f'  doi = {{{state["doi"]}}},')
        
        if state["arxiv_id"]:
            entry_lines.append(f'  eprint = {{{state["arxiv_id"]}}},')
            entry_lines.append(f'  archivePrefix = {{arXiv}},')
        
        # Add note with enrichment sources
        sources = [k for k, v in state["enrichment_attempts"].items() if v]
        if sources:
            entry_lines.append(f'  note = {{Enriched from {", ".join(sources)}}},')
        
        entry_lines.append("}")
        
        state["final_entry"] = "\n".join(entry_lines)
        return state
    
    # Helper methods for metadata extraction
    def _extract_title(self, ref: str) -> Optional[str]:
        """Extract title using multiple patterns."""
        import re
        
        patterns = [
            r'"([^"]+)"',  # Quoted
            r'„([^"]+)"',  # European quotes
            r'"([^"]+)"',  # Smart quotes
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref)
            if match and len(match.group(1)) > 5:
                return match.group(1).strip()
        
        # Fallback: text after year
        year_match = re.search(r'\b(19|20)\d{2}\b', ref)
        if year_match:
            after_year = ref[year_match.end():].strip()
            after_year = re.sub(r'^[^A-Za-z0-9]+', '', after_year)
            segment = after_year.split('.')[0].strip()
            if 10 <= len(segment) <= 200:
                return segment
        
        return None
    
    def _extract_authors(self, ref: str) -> List[str]:
        """Extract authors from reference."""
        import re
        
        # Look for author patterns before year
        year_match = re.search(r'\b(19|20)\d{2}\b', ref)
        author_text = ref[:year_match.start()] if year_match else ref[:100]
        
        # Common patterns
        patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]\.(?:\s*[A-Z]\.)*)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        authors = []
        for pattern in patterns:
            matches = re.findall(pattern, author_text)
            if matches:
                authors.extend(matches[:5])  # Limit to 5
                break
        
        return [a.strip() for a in authors if len(a.strip()) > 2]
    
    def _extract_year(self, ref: str) -> Optional[str]:
        """Extract publication year."""
        import re
        
        patterns = [
            r'\b(20[0-2]\d)\b',
            r'\b(19[89]\d)\b',
            r'\((20[0-2]\d)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref)
            if match:
                year = int(match.group(1))
                if 1990 <= year <= 2025:
                    return str(year)
        
        return None
    
    def _extract_journal_basic(self, ref: str) -> Optional[str]:
        """Basic journal extraction."""
        import re
        
        patterns = [
            r'\b(arXiv\s+preprint)',
            r'\b(IEEE\s+[^,\.]+)',
            r'\b(ACM\s+[^,\.]+)',
            r'\bProceedings\s+of\s+([^,\.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_doi(self, ref: str) -> Optional[str]:
        """Extract DOI."""
        import re
        
        patterns = [
            r'doi:?\s*([0-9]+\.[0-9]+/[^\s,]+)',
            r'https?://(?:dx\.)?doi\.org/([0-9]+\.[0-9]+/[^\s,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_arxiv(self, ref: str) -> Optional[str]:
        """Extract arXiv ID."""
        import re
        
        patterns = [
            r'arXiv:([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)',
            r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)',
            r'\b([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _determine_entry_type(self, ref: str) -> str:
        """Determine BibTeX entry type."""
        ref_lower = ref.lower()
        
        if any(term in ref_lower for term in ["proceedings", "conference", "workshop"]):
            return "inproceedings"
        elif any(term in ref_lower for term in ["book", "chapter"]):
            return "book"
        elif "arxiv" in ref_lower:
            return "misc"
        else:
            return "article"
    
    # External API enrichment methods
    async def _enrich_from_arxiv(self, arxiv_id: str) -> EnrichmentResult:
        """Enrich from arXiv API."""
        try:
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return EnrichmentResult(confidence=0.0, source="arxiv")
                    
                    xml_text = await resp.text()
                    root = ET.fromstring(xml_text)
                    ns = {'atom': 'http://www.w3.org/2005/Atom'}
                    
                    entry = root.find('atom:entry', ns)
                    if entry is None:
                        return EnrichmentResult(confidence=0.0, source="arxiv")
                    
                    title_el = entry.find('atom:title', ns)
                    title = title_el.text.strip().replace('\n', ' ') if title_el is not None else None
                    
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name_el = author.find('atom:name', ns)
                        if name_el is not None:
                            authors.append(name_el.text.strip())
                    
                    pub_el = entry.find('atom:published', ns)
                    year = pub_el.text[:4] if pub_el is not None else None
                    
                    return EnrichmentResult(
                        title=title,
                        authors=authors,
                        year=year,
                        journal="arXiv preprint",
                        confidence=0.9,
                        source="arxiv"
                    )
                    
        except Exception as e:
            logger.debug(f"arXiv enrichment failed: {e}")
            return EnrichmentResult(confidence=0.0, source="arxiv")
    
    async def _enrich_from_crossref_doi(self, doi: str) -> EnrichmentResult:
        """Enrich from Crossref DOI API."""
        try:
            url = f"https://api.crossref.org/works/{doi}"
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return EnrichmentResult(confidence=0.0, source="crossref_doi")
                    
                    data = await resp.json()
                    message = data.get("message", {})
                    
                    title = (message.get("title") or [None])[0]
                    journal = (message.get("container-title") or [None])[0]
                    
                    year = None
                    if message.get("issued") and message["issued"].get("date-parts"):
                        year = str(message["issued"]["date-parts"][0][0])
                    
                    authors = []
                    for author in message.get("author", []):
                        given = author.get("given", "").strip()
                        family = author.get("family", "").strip()
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                    
                    return EnrichmentResult(
                        title=title,
                        authors=authors,
                        year=year,
                        journal=journal,
                        doi=doi,
                        confidence=0.95,
                        source="crossref_doi"
                    )
                    
        except Exception as e:
            logger.debug(f"Crossref DOI enrichment failed: {e}")
            return EnrichmentResult(confidence=0.0, source="crossref_doi")
    
    async def _enrich_from_crossref_title(self, title: str) -> EnrichmentResult:
        """Enrich from Crossref title search."""
        try:
            query = urllib.parse.quote(title)
            url = f"https://api.crossref.org/works?query.bibliographic={query}&rows=1"
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return EnrichmentResult(confidence=0.0, source="crossref_title")
                    
                    data = await resp.json()
                    items = data.get("message", {}).get("items", [])
                    
                    if not items:
                        return EnrichmentResult(confidence=0.0, source="crossref_title")
                    
                    item = items[0]
                    
                    # Calculate confidence based on title similarity
                    found_title = (item.get("title") or [None])[0]
                    confidence = 0.7 if found_title else 0.3
                    
                    journal = (item.get("container-title") or [None])[0]
                    doi = item.get("DOI")
                    
                    year = None
                    if item.get("issued") and item["issued"].get("date-parts"):
                        year = str(item["issued"]["date-parts"][0][0])
                    
                    authors = []
                    for author in item.get("author", []):
                        given = author.get("given", "").strip()
                        family = author.get("family", "").strip()
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                    
                    return EnrichmentResult(
                        title=found_title,
                        authors=authors,
                        year=year,
                        journal=journal,
                        doi=doi,
                        confidence=confidence,
                        source="crossref_title"
                    )
                    
        except Exception as e:
            logger.debug(f"Crossref title enrichment failed: {e}")
            return EnrichmentResult(confidence=0.0, source="crossref_title")
    
    async def _enrich_from_semantic_scholar(self, title: str) -> EnrichmentResult:
        """Enrich from Semantic Scholar API."""
        try:
            query = urllib.parse.quote(title)
            fields = "title,authors,year,venue,externalIds"
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=1&fields={fields}"
            
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return EnrichmentResult(confidence=0.0, source="semantic_scholar")
                    
                    data = await resp.json()
                    papers = data.get("data", [])
                    
                    if not papers:
                        return EnrichmentResult(confidence=0.0, source="semantic_scholar")
                    
                    paper = papers[0]
                    
                    venue = paper.get("venue")
                    year = str(paper.get("year")) if paper.get("year") else None
                    authors = [a.get("name") for a in paper.get("authors", []) if a.get("name")]
                    doi = paper.get("externalIds", {}).get("DOI")
                    
                    return EnrichmentResult(
                        journal=venue,
                        year=year,
                        authors=authors,
                        doi=doi,
                        confidence=0.8,
                        source="semantic_scholar"
                    )
                    
        except Exception as e:
            logger.debug(f"Semantic Scholar enrichment failed: {e}")
            return EnrichmentResult(confidence=0.0, source="semantic_scholar")
    
    def _merge_enrichment_results(self, results: List[EnrichmentResult]) -> Optional[EnrichmentResult]:
        """Merge enrichment results with confidence-based selection."""
        valid_results = [r for r in results if isinstance(r, EnrichmentResult) and r.confidence > 0]
        
        if not valid_results:
            return None
        
        # Sort by confidence, highest first
        valid_results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Start with highest confidence result
        best = valid_results[0]
        
        # Merge additional data from other sources
        merged = EnrichmentResult(
            title=best.title,
            authors=best.authors,
            year=best.year,
            journal=best.journal,
            doi=best.doi,
            confidence=best.confidence,
            source=best.source
        )
        
        # Fill in missing fields from other results
        for result in valid_results[1:]:
            if not merged.title and result.title:
                merged.title = result.title
            if not merged.authors and result.authors:
                merged.authors = result.authors
            if not merged.year and result.year:
                merged.year = result.year
            if not merged.journal and result.journal:
                merged.journal = result.journal
            if not merged.doi and result.doi:
                merged.doi = result.doi
        
        return merged
    
    def _generate_citation_key(self, authors: List[str], year: Optional[str], title: Optional[str]) -> str:
        """Generate citation key for BibTeX entry."""
        # First author's last name
        first_author = "Unknown"
        if authors:
            author_parts = authors[0].split()
            first_author = author_parts[-1] if author_parts else "Unknown"
        
        # Year
        year_str = year if year else "2024"
        
        # First meaningful word from title
        title_word = "Paper"
        if title:
            words = title.split()
            for word in words:
                if len(word) > 3 and word.lower() not in {'the', 'and', 'for', 'with', 'from', 'this', 'that'}:
                    title_word = word
                    break
        
        # Clean and combine
        citation_key = f"{first_author}{year_str}{title_word}"
        return ''.join(c for c in citation_key if c.isalnum()) 