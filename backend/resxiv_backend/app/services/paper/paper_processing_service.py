"""
Paper Processing Service - L6 Engineering Standards  
Focused on GROBID integration and metadata extraction operations.
"""

import os
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import aiohttp
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.paper_repository import PaperRepository

import uuid
import asyncio

logger = logging.getLogger(__name__)


class PaperProcessingService:
    """
    Processing service for paper metadata extraction.
    Single Responsibility: GROBID processing and metadata extraction.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaperRepository(session)
        
        # GROBID configuration
        self.grobid_url = os.getenv("GROBID_URL", "http://localhost:8070")
        self.grobid_timeout = 120
        
        # Storage configuration
        self.base_dir = Path(os.getenv("RESXIV_DATA_DIR", "/ResXiv_V2"))
        self.xml_dir = self.base_dir / "xml"
        self.xml_dir.mkdir(exist_ok=True, parents=True)
        self.bib_dir = self.base_dir / "bib"
        self.bib_dir.mkdir(exist_ok=True, parents=True)
    
    @handle_service_errors("check GROBID availability")
    async def check_grobid_health(self) -> Dict[str, Any]:
        """
        Check if GROBID service is available.
        
        Returns:
            Health check result
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.grobid_url}/api/isalive",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return {
                            "success": True,
                            "status": "healthy",
                            "grobid_url": self.grobid_url
                        }
                    else:
                        return {
                            "success": False,
                            "status": "unhealthy",
                            "error": f"GROBID returned status {response.status}"
                        }
        except Exception as e:
            return {
                "success": False,
                "status": "unavailable", 
                "error": str(e)
            }
    
    @handle_service_errors("process paper with GROBID")
    async def process_with_grobid(
        self,
        file_path: Path,
        paper_id: str
    ) -> Dict[str, Any]:
        """
        Process PDF with GROBID to extract metadata and structure.
        
        Args:
            file_path: Path to PDF file
            paper_id: Paper UUID
            
        Returns:
            Processing result with extracted metadata
        """
        if not file_path.exists():
            raise ServiceError(
                "File not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        if file_path.suffix.lower() != '.pdf':
            raise ServiceError(
                "GROBID processing only supports PDF files",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Check GROBID availability
        health_check = await self.check_grobid_health()
        if not health_check["success"]:
            raise ServiceError(
                f"GROBID service unavailable: {health_check.get('error', 'Unknown error')}",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare file for upload
                data = aiohttp.FormData()
                
                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()
                    data.add_field('input', file_content, filename=file_path.name, content_type='application/pdf')
                
                # Send to GROBID
                async with session.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.grobid_timeout)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GROBID API error {response.status}: {error_text}")
                        raise ServiceError(
                            f"GROBID processing failed with status {response.status}: {error_text}",
                            ErrorCodes.EXTERNAL_SERVICE_ERROR
                        )
                    
                    # Get TEI-XML result
                    tei_xml = await response.text()
                    
                    # Log GROBID response info
                    logger.info(f"GROBID returned {len(tei_xml)} characters of TEI-XML for paper {paper_id}")
                    
                    # Store XML file
                    xml_filename = f"{paper_id}.xml"
                    xml_path = self.xml_dir / xml_filename
                    
                    async with aiofiles.open(xml_path, 'w', encoding='utf-8') as f:
                        await f.write(tei_xml)
                    
                    # Extract metadata from TEI-XML
                    metadata = await self._extract_metadata_from_tei(tei_xml)
                    
                    # Add XML path to metadata for paper record update
                    metadata["xml_path"] = str(xml_path.relative_to(self.base_dir))

                    # Always attempt to save bibliography if ANY references extracted
                    if metadata.get("references") and len(metadata["references"]) > 0:
                        try:
                            bib_rel_path = await self._save_bib_file(paper_id, metadata["references"])
                            metadata["bib_path"] = bib_rel_path
                            logger.info(f"Created bib file with {len(metadata['references'])} references: {bib_rel_path}")
                            print(f"✅ BIB FILE CREATED: {self.base_dir / bib_rel_path}")
                        except Exception as e:
                            logger.warning(f"Failed to create bib file for paper {paper_id}: {e}")
                            # Don't fail GROBID processing if bib creation fails
                    else:
                        logger.info(f"No references found in GROBID extraction for paper {paper_id}")

                        # Fallback: try GROBID's dedicated reference extraction endpoint
                        try:
                            fallback_refs = await self._extract_references_only(file_path)
                            if fallback_refs:
                                try:
                                    bib_rel_path = await self._save_bib_file(paper_id, fallback_refs)
                                    metadata["bib_path"] = bib_rel_path
                                    metadata["references"] = fallback_refs
                                    logger.info(
                                        f"Created bib file via fallback extraction with {len(fallback_refs)} references: {bib_rel_path}"
                                    )
                                    print(f"✅ BIB FILE CREATED (FALLBACK): {self.base_dir / bib_rel_path}")
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to create bib file from fallback references for paper {paper_id}: {e}"
                                    )
                        except Exception as e:
                            logger.warning(
                                f"Fallback reference extraction failed for paper {paper_id}: {e}"
                            )

                    return {
                        "success": True,
                        "metadata": metadata,
                        "tei_xml_path": str(xml_path.relative_to(self.base_dir)),
                        "paper_id": paper_id
                    }
                    
        except aiohttp.ClientError as e:
            raise ServiceError(
                f"Network error during GROBID processing: {str(e)}",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
        except Exception as e:
            raise ServiceError(
                f"GROBID processing failed: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def _extract_metadata_from_tei(self, tei_xml: str) -> Dict[str, Any]:
        """
        Extract metadata from TEI-XML format.
        
        Args:
            tei_xml: TEI-XML content from GROBID
            
        Returns:
            Extracted metadata
            
        Raises:
            ServiceError: If GROBID returns empty or invalid content
        """
        import xml.etree.ElementTree as ET
        import re

        # Initialize metadata container
        metadata: Dict[str, Any] = {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "references": [],
            "sections": [],
            "full_text": ""
        }

        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError as e:
            raise ServiceError(
                f"Invalid TEI-XML format from GROBID: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )

        # Register TEI namespace - CRITICAL for GROBID parsing
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        print(f"🔍 DEBUG: Root tag = {root.tag}")
        print(f"🔍 DEBUG: Root attributes = {root.attrib}")

        # --- Title ---
        title_patterns = [
            './/tei:title[@level="a"]',
            './/tei:title[@type="main"]', 
            './/tei:title',
            './/title[@level="a"]',  # fallback without namespace
            './/title[@type="main"]',
            './/title'
        ]
        title_el = None
        for pattern in title_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    title_el = root.find(pattern, ns)
                else:
                    title_el = root.find(pattern)
                if title_el is not None:
                    break
            except:
                continue
                
        if title_el is not None and title_el.text:
            metadata["title"] = self._clean_title(title_el.text)
            print(f"✅ TITLE FOUND: {metadata['title']}")

        # --- Abstract ---
        abstract_patterns = [
            './/tei:abstract',
            './/tei:div[@type="abstract"]',
            './/abstract',  # fallback
            './/div[@type="abstract"]'
        ]
        abstract_el = None
        for pattern in abstract_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    abstract_el = root.find(pattern, ns)
                else:
                    abstract_el = root.find(pattern)
                if abstract_el is not None:
                    break
            except:
                continue
                
        if abstract_el is not None:
            abstract_text = ' '.join(abstract_el.itertext()).strip()
            metadata["abstract"] = re.sub(r'\s+', ' ', abstract_text)
            print(f"✅ ABSTRACT FOUND: {len(metadata['abstract'])} chars")

        # --- Authors ---
        # Restrict search to the TEI header to avoid picking up authors of cited references
        tei_header = root.find('.//tei:teiHeader', ns)
        author_candidates = []
        if tei_header is not None:
            author_patterns = [
                './/tei:fileDesc//tei:sourceDesc//tei:biblStruct//tei:analytic//tei:author',
                './/tei:profileDesc//tei:author',
                './/tei:fileDesc//tei:titleStmt//tei:author',
                './/tei:author'
            ]
            for pattern in author_patterns:
                try:
                    authors_found = tei_header.findall(pattern, ns)
                    for pers in authors_found:
                        # Build full name from forename + surname if available, else text content
                        forename = pers.find('.//tei:forename', ns)
                        surname = pers.find('.//tei:surname', ns)
                        if forename is not None and surname is not None:
                            full_name = f"{forename.text.strip()} {surname.text.strip()}"
                        else:
                            full_name = ' '.join(pers.itertext()).strip()
                        if full_name and full_name not in author_candidates:
                            author_candidates.append(full_name)
                except Exception:
                    continue

        # Fallback to original broad search only if header extraction failed
        if not author_candidates:
            broad_patterns = [
                './/tei:author//tei:persName',
                './/tei:byline//tei:persName',
            ]
            for pattern in broad_patterns:
                try:
                    authors_found = root.findall(pattern, ns)
                    for pers in authors_found:
                        full_name = ' '.join(pers.itertext()).strip()
                        if full_name and full_name not in author_candidates:
                            author_candidates.append(full_name)
                except Exception:
                    continue

        # Keep only up to 20 unique authors
        metadata["authors"] = author_candidates[:20]

        print(f"✅ AUTHORS FOUND: {len(metadata['authors'])} - {metadata['authors']}")

        # --- Keywords ---
        keyword_patterns = [
            './/tei:keywords//tei:term',
            './/tei:keyword',
            './/tei:classCode',
            './/keywords//term',  # fallback
            './/keyword',
            './/classCode'
        ]
        
        for pattern in keyword_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    keywords_found = root.findall(pattern, ns)
                else:
                    keywords_found = root.findall(pattern)
                    
                for kw_el in keywords_found:
                    kw_text = kw_el.text.strip() if kw_el.text else ''
                    if kw_text and kw_text not in metadata["keywords"]:
                        metadata["keywords"].append(kw_text)
            except:
                continue

        # --- References ---
        ref_patterns = [
            './/tei:listBibl//tei:biblStruct',
            './/tei:listBibl//tei:bibl', 
            './/tei:bibliography//tei:bibl',
            './/tei:back//tei:listBibl//tei:bibl',
            './/tei:div[@type="bibliography"]//tei:biblStruct',
            './/tei:div[@type="references"]//tei:biblStruct',
            './/tei:ref',
            './/listBibl//biblStruct',  # fallback
            './/listBibl//bibl',
            './/bibliography//bibl',
            './/back//listBibl//bibl',
            './/div[@type="bibliography"]//biblStruct',
            './/div[@type="references"]//biblStruct', 
            './/ref'
        ]
        
        for pattern in ref_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    refs_found = root.findall(pattern, ns)
                else:
                    refs_found = root.findall(pattern)
                    
                for bibl in refs_found:
                    ref_text = ' '.join(bibl.itertext()).strip()
                    ref_text = re.sub(r'\s+', ' ', ref_text)
                    if ref_text and ref_text not in metadata["references"]:
                        metadata["references"].append(ref_text)
            except:
                continue
                
        print(f"✅ REFERENCES FOUND: {len(metadata['references'])}")

        # --- Sections --- (headings)
        section_patterns = [
            './/tei:div[@type="section"]//tei:head',
            './/tei:div//tei:head',
            './/tei:section//tei:title',
            './/tei:head',
            './/div[@type="section"]//head',  # fallback
            './/div//head',
            './/section//title',
            './/head'
        ]
        
        for pattern in section_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    sections_found = root.findall(pattern, ns)
                else:
                    sections_found = root.findall(pattern)
                    
                for head in sections_found:
                    sect = head.text.strip() if head.text else ''
                    if sect and sect not in metadata["sections"]:
                        metadata["sections"].append(sect)
            except:
                continue
         
        # --- Extract full text content for diagnostics ---
        full_text_parts = []
        text_patterns = [
            './/tei:text//tei:p',
            './/tei:body//tei:p',
            './/text//p',  # fallback
            './/body//p',
            './/p'
        ]
        
        for pattern in text_patterns:
            try:
                if pattern.startswith('.//tei:'):
                    paragraphs = root.findall(pattern, ns)
                else:
                    paragraphs = root.findall(pattern)
                    
                for p in paragraphs:
                    paragraph_text = ' '.join(p.itertext()).strip()
                    if paragraph_text:
                        full_text_parts.append(paragraph_text)
                        
                if full_text_parts:  # Stop after first successful pattern
                    break
            except:
                continue
         
        metadata["full_text"] = ' '.join(full_text_parts)
        print(f"✅ FULL TEXT EXTRACTED: {len(metadata['full_text'])} chars")
         
        # Log extraction results for monitoring (no validation rejection)
        logger.info(f"GROBID extraction results - Title: {bool(metadata['title'])}, Abstract: {len(metadata['abstract'])} chars, Authors: {len(metadata['authors'])}, Full text: {len(metadata['full_text'])} chars, References: {len(metadata['references'])}")
            
        return metadata
    
    async def _save_bib_file(self, paper_id: str, references: list[str]) -> str:
        """
        Production-grade BibTeX generation using LangGraph agent.
        
        Args:
            paper_id: Paper UUID
            references: List of reference strings from GROBID
            
        Returns:
            Relative path to the saved file
        """
        if not references:
            raise ServiceError(
                "No references found to create bib file",
                ErrorCodes.PROCESSING_ERROR
            )
        
        from .bibliography_agent import BibliographyEnrichmentAgent
        from .bib_parser import BibParser
        
        bib_filename = f"{paper_id}.bib"
        bib_path = self.bib_dir / bib_filename
        
        # Initialize LangGraph agent
        agent = BibliographyEnrichmentAgent(timeout=10)
        
        # Process references in parallel with controlled concurrency
        logger.info(f"Processing {len(references)} references with LangGraph agent")
        
        # Limit concurrent requests to avoid overwhelming APIs
        semaphore = asyncio.Semaphore(3)
        
        async def process_reference(ref_data):
            ref, idx = ref_data
            async with semaphore:
                return await agent.enrich_reference(ref, idx + 1)
        
        # Process references concurrently
        tasks = [process_reference((ref, i)) for i, ref in enumerate(references)]
        bib_entries = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid entries
        valid_entries = [
            entry for entry in bib_entries 
            if isinstance(entry, str) and entry.strip()
        ]
        
        if not valid_entries:
            raise ServiceError(
                "No valid references found to create meaningful bib file",
                ErrorCodes.PROCESSING_ERROR
            )
        
        # Create header with processing stats
        processing_stats = {
            "total_references": len(references),
            "valid_entries": len(valid_entries),
            "success_rate": f"{len(valid_entries)/len(references)*100:.1f}%"
        }
        
        header = f"""% Bibliography extracted and enriched for paper: {paper_id}
% Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
% Processing stats: {processing_stats['total_references']} refs → {processing_stats['valid_entries']} entries ({processing_stats['success_rate']} success)
% Enrichment sources: arXiv, Crossref, Semantic Scholar
% Agent: LangGraph-based bibliography enrichment
% 
% This bibliography was automatically generated with external API enrichment.
% Entries include enriched metadata from multiple academic sources.

"""
        
        bib_content = header + "\n\n".join(valid_entries)
        
        # Write file
        async with aiofiles.open(bib_path, 'w', encoding='utf-8') as f:
            await f.write(bib_content)
        
        # Validate generated BibTeX using parser
        try:
            parsed_papers = BibParser.parse_content(bib_content)
            validated_count = sum(1 for paper in parsed_papers if BibParser.validate_entry(paper))
            
            logger.info(f"Generated {len(valid_entries)} BibTeX entries, {validated_count} validated successfully")
            print(f"📄 BIB FILE SAVED: {bib_path} ({len(valid_entries)} entries, {validated_count} validated)")
            
        except Exception as e:
            logger.warning(f"BibTeX validation failed: {e}")
            print(f"📄 BIB FILE SAVED: {bib_path} ({len(valid_entries)} entries, validation skipped)")
        
        return str(bib_path.relative_to(self.base_dir))
    
    @handle_service_errors("extract text with PyPDF")
    async def extract_text_with_pypdf(
        self,
        file_path: Path,
        paper_id: str
    ) -> Dict[str, Any]:
        """
        Extract raw text content using PyPDF for AI diagnostics.
        This is separate from GROBID processing.
        
        Args:
            file_path: Path to PDF file
            paper_id: Paper UUID
            
        Returns:
            Extracted text content result
        """
        try:
            import PyPDF2
            import io
            
            # Read PDF and extract text
            text_content = []
            page_count = 0
            
            async with aiofiles.open(file_path, 'rb') as f:
                pdf_content = await f.read()
                
            # Use PyPDF2 to extract text
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            page_count = len(pdf_reader.pages)
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(page_text.strip())
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1} of paper {paper_id}: {e}")
                    continue
            
            # Combine all text
            full_text = '\n\n'.join(text_content)
            word_count = len(full_text.split()) if full_text else 0
            
            # Validate we got meaningful text
            if not full_text or word_count < 50:
                raise ServiceError(
                    f"PyPDF extraction yielded insufficient text content ({word_count} words)",
                    ErrorCodes.PROCESSING_ERROR
                )
            
            logger.info(f"PyPDF extracted {word_count} words from {page_count} pages for paper {paper_id}")
            
            return {
                "success": True,
                "text_content": full_text,
                "word_count": word_count,
                "page_count": page_count,
                "extraction_method": "pypdf"
            }
            
        except ImportError:
            raise ServiceError(
                "PyPDF2 library not available for text extraction",
                ErrorCodes.PROCESSING_ERROR
            )
        except Exception as e:
            raise ServiceError(
                f"PyPDF text extraction failed: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )
    
    def _clean_title(self, raw_title: str) -> str:
        """Clean title by removing copyright and attribution text."""
        import re
        
        # Remove boiler-plate copyright / permission headers that often precede real titles
        patterns_to_remove = [
            r'^.*?(grants permission|provided proper attribution|all rights reserved|copyright|©).*?\.\s*',
            r'^permission to reproduce.*?\.\s*',
        ]
        
        cleaned = raw_title
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Collapse whitespace and strip
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Heuristic: pick the sentence with maximum number of capitalised words assuming it is the real title
        if len(cleaned) < 10:
            sentences = [s.strip() for s in re.split(r'[.!?]', raw_title) if len(s.strip()) > 5]
            def score(sent: str) -> int:
                return sum(1 for w in sent.split() if w[:1].isupper())
            if sentences:
                cleaned = max(sentences, key=score)
         
        # Final fallback - take last meaningful words
        if len(cleaned) < 5:
            words = [w for w in raw_title.split() if w.isalpha()]
            if len(words) >= 4:
                cleaned = ' '.join(words[-6:])
         
        return cleaned.strip() if len(cleaned.strip()) > 3 else "Untitled Document"
    
    @handle_service_errors("get processing status")
    async def get_processing_status(self, paper_id: str) -> Dict[str, Any]:
        """
        Get processing status for a paper.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Processing status
        """
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Check if XML file exists
        xml_path = self.xml_dir / f"{paper_id}.xml"
        xml_exists = xml_path.exists()
        
        return {
            "success": True,
            "paper_id": paper_id,
            "processing_status": {
                "grobid_processed": xml_exists,
                "metadata_extracted": bool(paper.abstract or paper.authors),
                "text_extracted": bool(paper.content),
                "last_processed": paper.updated_at.isoformat() if paper.updated_at else None
            }
        }
    
    @handle_service_errors("cleanup processing files")
    async def cleanup_processing_files(self, paper_id: str) -> Dict[str, Any]:
        """
        Clean up processing files for a paper.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Cleanup result
        """
        cleaned_files = []
        
        # Remove XML file
        xml_path = self.xml_dir / f"{paper_id}.xml"
        if xml_path.exists():
            xml_path.unlink()
            cleaned_files.append(str(xml_path))
        
        return {
            "success": True,
            "cleaned_files": cleaned_files,
            "message": f"Cleaned {len(cleaned_files)} processing files"
        } 