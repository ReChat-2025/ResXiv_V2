"""
AI Diagnostics Service - GPT-4o Mini Integration
Generates comprehensive paper diagnostics using AI analysis.
"""

import logging
from typing import Dict, Any, Optional
import json

from openai import AsyncOpenAI
from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)

class AIDiagnosticsService:
    """
    AI-powered diagnostics generation using GPT-4o mini.
    Single Responsibility: AI analysis of paper content for diagnostics.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.agentic.openai_api_key)
        self.model = "gpt-4o-mini"
        self.max_tokens = 2500  # Increased for detailed researcher-focused analysis
        
    @handle_service_errors("generate AI diagnostics")
    async def generate_diagnostics_from_text(
        self,
        title: str,
        abstract: str,
        full_text: str,
        paper_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive diagnostics using GPT-4o mini.
        
        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full extracted text content
            paper_metadata: Additional metadata from GROBID
            
        Returns:
            Comprehensive diagnostics dict
        """
        if not full_text or len(full_text.strip()) < 100:
            raise ServiceError(
                "Insufficient text content for AI diagnostics generation",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Prepare content for analysis
        content_for_analysis = self._prepare_content_for_analysis(
            title, abstract, full_text, paper_metadata
        )
        
        try:
            # Generate diagnostics using GPT-4o mini
            diagnostics_response = await self._call_gpt4o_mini(content_for_analysis)
            
            # Parse and validate response
            diagnostics = self._parse_diagnostics_response(diagnostics_response)
            
            return {
                "success": True,
                "diagnostics": diagnostics,
                "model_used": self.model,
                "content_length": len(content_for_analysis)
            }
            
        except Exception as e:
            raise ServiceError(
                f"AI diagnostics generation failed: {str(e)}",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
    
    def _prepare_content_for_analysis(
        self,
        title: str,
        abstract: str,
        full_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare content for AI analysis with context."""
        content_parts = []
        
        if title:
            content_parts.append(f"TITLE: {title}")
        
        if abstract:
            content_parts.append(f"ABSTRACT: {abstract}")
        
        if metadata:
            authors = metadata.get("authors", [])
            if authors:
                content_parts.append(f"AUTHORS: {', '.join(authors[:5])}")
            
            sections = metadata.get("sections", [])
            if sections:
                content_parts.append(f"SECTIONS: {', '.join(sections[:10])}")
        
        # Truncate full text to avoid token limits
        max_text_length = 4000  # Conservative limit
        if len(full_text) > max_text_length:
            full_text = full_text[:max_text_length] + "... [truncated]"
        
        content_parts.append(f"FULL TEXT: {full_text}")
        
        return "\n\n".join(content_parts)
    
    async def _call_gpt4o_mini(self, content: str) -> str:
        """Call GPT-4o mini API for diagnostics generation."""
        system_prompt = """You are a senior research scientist and academic paper reviewer with expertise across multiple domains. Your role is to provide comprehensive, researcher-focused diagnostics that help academics quickly understand and evaluate research papers.

Analyze the provided paper with the depth and rigor expected in academic peer review. Return a JSON object with these exact fields:

- "summary": A comprehensive 3-4 sentence academic summary covering: (1) the research problem addressed, (2) the proposed approach/method, (3) key experimental findings, and (4) broader implications for the field

- "method": Detailed methodology analysis including: experimental design, theoretical framework, technical approach, validation strategy, and any novel methodological contributions. Be specific about algorithms, models, or techniques used

- "dataset": Complete information about data sources including: dataset names, sizes, characteristics, preprocessing steps, evaluation metrics, and any data limitations or biases that could affect conclusions

- "highlights": 3-4 significant research contributions presented as bullet points, focusing on: novel theoretical insights, empirical discoveries, methodological innovations, performance improvements, or validation of hypotheses

- "weakness": Critical academic weaknesses including: methodological flaws, experimental design issues, theoretical gaps, insufficient baselines, limited scope, statistical concerns, or reproducibility issues

- "limitations": Specific constraints and boundaries of the study including: scope limitations, data constraints, methodological boundaries, generalizability limits, or inherent study restrictions

- "future_scope": Specific research directions that emerge from this work, including: unexplored extensions, methodological improvements, broader applications, theoretical questions raised, or gaps identified for future investigation

- "strengths": Academic strengths including: methodological rigor, experimental design quality, theoretical soundness, comprehensive evaluation, novelty of approach, clarity of presentation, or significance of results

- "contributions": Primary scholarly contributions to the research field, including: advancement of knowledge, practical applications, theoretical insights, methodological innovations, or empirical evidence provided

Focus on aspects most valuable to researchers: reproducibility, methodological soundness, theoretical contributions, empirical significance, and potential for building upon this work. If specific information is not available in the text, state "Not clearly specified in the provided text" rather than inferring."""

        user_prompt = f"""As a senior research scientist, conduct a thorough academic evaluation of this paper. Focus on aspects that would be most valuable to fellow researchers who may want to:
1. Understand the core contributions and methodology
2. Assess the validity and reliability of the findings  
3. Evaluate whether to cite this work or build upon it
4. Identify potential collaboration or extension opportunities

Provide detailed, research-grade diagnostics for:

{content}"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=0.3,  # Low temperature for consistency
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    
    def _parse_diagnostics_response(self, response: str) -> Dict[str, str]:
        """Parse and validate GPT-4o mini response."""
        try:
            diagnostics = json.loads(response)
            
            # Required fields for diagnostics
            required_fields = [
                "summary", "method", "dataset", "highlights", 
                "weakness", "limitations", "future_scope", "strengths", "contributions"
            ]
            
            # Ensure all required fields are present and handle different data types
            for field in required_fields:
                if field not in diagnostics:
                    diagnostics[field] = "Not clearly specified"
                else:
                    # Handle case where GPT returns a list instead of string
                    if isinstance(diagnostics[field], list):
                        diagnostics[field] = "; ".join(str(item) for item in diagnostics[field] if item)
                    elif not diagnostics[field] or (isinstance(diagnostics[field], str) and diagnostics[field].strip() == ""):
                        diagnostics[field] = "Not clearly specified"
            
            # Clean up the content - ensure all values are strings
            for field in diagnostics:
                if isinstance(diagnostics[field], str):
                    diagnostics[field] = diagnostics[field].strip()
                elif diagnostics[field] is None:
                    diagnostics[field] = "Not clearly specified"
                else:
                    # Convert non-string types to string
                    diagnostics[field] = str(diagnostics[field]).strip()
            
            return diagnostics
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4o mini response: {e}")
            # Fallback diagnostics
            return {
                "summary": "AI analysis failed - manual review required",
                "method": "Not clearly specified",
                "dataset": "Not clearly specified", 
                "highlights": "Analysis could not be completed",
                "weakness": "AI processing error occurred",
                "future_scope": "Manual analysis recommended",
                "strengths": "Not clearly specified",
                "contributions": "Not clearly specified"
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing diagnostics response: {e}")
            return {
                "summary": "AI analysis encountered an error",
                "method": "Not clearly specified",
                "dataset": "Not clearly specified", 
                "highlights": "Processing error occurred",
                "weakness": "Unable to analyze due to technical issues",
                "future_scope": "Manual review required",
                "strengths": "Not clearly specified",
                "contributions": "Not clearly specified"
            } 