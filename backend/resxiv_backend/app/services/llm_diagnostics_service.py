"""
LLM Diagnostics Service

Handles LLM-based paper analysis and diagnostics generation using
OpenAI GPT models or local Ollama models for paper analysis.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class LLMDiagnosticsService:
    """Service for generating paper diagnostics using LLM models"""
    
    def __init__(self, model_type: str = "openai", model_name: str = None):
        """
        Initialize the LLM diagnostics service
        
        Args:
            model_type: Type of model to use ("openai" or "ollama")
            model_name: Specific model name to use
        """
        self.model_type = model_type.lower()
        self.model_name = model_name
        
        # Set default model names
        if not self.model_name:
            if self.model_type == "openai":
                self.model_name = "gpt-4o-mini"
            else:  # ollama
                self.model_name = "llama3.2:latest"
        
        # Initialize clients
        self.openai_client = None
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        if self.model_type == "openai":
            self._initialize_openai()
    
    def _initialize_openai(self) -> None:
        """Initialize OpenAI client"""
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self.openai_client = openai.AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise
    
    async def generate_diagnostics(
        self,
        paper_content: str,
        paper_title: str,
        paper_abstract: str = None,
        include_sections: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive diagnostics for a paper
        
        Args:
            paper_content: Full text content of the paper
            paper_title: Paper title
            paper_abstract: Paper abstract (optional)
            include_sections: Sections to include in diagnostics
            
        Returns:
            Diagnostics result dictionary
        """
        try:
            logger.info(f"Generating diagnostics for paper: {paper_title}")
            
            # Default sections if not specified
            if not include_sections:
                include_sections = [
                    "summary", "method", "strengths", "limitations", 
                    "contributions", "future_scope"
                ]
            
            # Prepare content for analysis
            analysis_content = self._prepare_content_for_analysis(
                paper_content, paper_title, paper_abstract
            )
            
            # Generate diagnostics based on model type
            if self.model_type == "openai":
                result = await self._generate_with_openai(analysis_content, include_sections)
            else:
                result = await self._generate_with_ollama(analysis_content, include_sections)
            
            return {
                "success": True,
                "diagnostics": result,
                "model_used": f"{self.model_type}:{self.model_name}",
                "sections_included": include_sections
            }
            
        except Exception as e:
            logger.error(f"Error generating diagnostics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "diagnostics": None
            }
    
    def _prepare_content_for_analysis(
        self,
        paper_content: str,
        paper_title: str,
        paper_abstract: str = None
    ) -> str:
        """
        Prepare paper content for LLM analysis
        
        Args:
            paper_content: Full paper content
            paper_title: Paper title
            paper_abstract: Paper abstract
            
        Returns:
            Formatted content for analysis
        """
        # Limit content length to avoid token limits
        max_content_length = 15000  # Approximately 3500-4000 tokens
        
        if len(paper_content) > max_content_length:
            # Take first part of the paper (introduction, methodology)
            paper_content = paper_content[:max_content_length] + "...\n[Content truncated]"
        
        # Format content
        formatted_content = f"Title: {paper_title}\n\n"
        
        if paper_abstract:
            formatted_content += f"Abstract: {paper_abstract}\n\n"
        
        formatted_content += f"Paper Content:\n{paper_content}"
        
        return formatted_content
    
    async def _generate_with_openai(
        self,
        content: str,
        include_sections: List[str]
    ) -> Dict[str, str]:
        """
        Generate diagnostics using OpenAI GPT models
        
        Args:
            content: Prepared paper content
            include_sections: Sections to include
            
        Returns:
            Generated diagnostics dictionary
        """
        try:
            # Create prompt for diagnostics
            prompt = self._create_diagnostics_prompt(include_sections)
            
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI diagnostics generation error: {str(e)}")
            raise
    
    async def _generate_with_ollama(
        self,
        content: str,
        include_sections: List[str]
    ) -> Dict[str, str]:
        """
        Generate diagnostics using Ollama local models
        
        Args:
            content: Prepared paper content
            include_sections: Sections to include
            
        Returns:
            Generated diagnostics dictionary
        """
        try:
            import aiohttp
            
            # Create prompt for diagnostics
            prompt = self._create_diagnostics_prompt(include_sections, format_json=True)
            full_prompt = f"{prompt}\n\nPaper to analyze:\n{content}"
            
            url = f"{self.ollama_base_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2000
                }
            }
            
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API returned status {response.status}")
                    
                    result = await response.json()
                    response_text = result.get("response", "")
                    
                    # Try to parse JSON response
                    try:
                        # Extract JSON from response if it's wrapped in other text
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            json_text = response_text[json_start:json_end]
                            return json.loads(json_text)
                        else:
                            # Fallback: parse as structured text
                            return self._parse_structured_response(response_text, include_sections)
                    except json.JSONDecodeError:
                        # Fallback: parse as structured text
                        return self._parse_structured_response(response_text, include_sections)
            
        except Exception as e:
            logger.error(f"Ollama diagnostics generation error: {str(e)}")
            raise
    
    def _create_diagnostics_prompt(self, include_sections: List[str], format_json: bool = True) -> str:
        """
        Create prompt for diagnostics generation
        
        Args:
            include_sections: Sections to include in diagnostics
            format_json: Whether to format as JSON
            
        Returns:
            Formatted prompt string
        """
        sections_description = {
            "summary": "A comprehensive 2-3 sentence summary of the paper's main contribution and findings",
            "method": "Description of the methodology, approach, or techniques used in the research",
            "strengths": "Key strengths and positive aspects of the research",
            "limitations": "Limitations, weaknesses, or areas for improvement",
            "contributions": "Main contributions and novel aspects of the work",
            "future_scope": "Potential future research directions and applications",
            "dataset": "Information about datasets used, if any",
            "highlights": "Key highlights and important findings from the paper"
        }
        
        if format_json:
            prompt = """You are an expert research paper analyst. Analyze the given research paper and provide structured diagnostics in JSON format.

Return your analysis as a valid JSON object with the following structure:
{"""
            
            for section in include_sections:
                if section in sections_description:
                    prompt += f'\n  "{section}": "{sections_description[section]}",'
            
            prompt = prompt.rstrip(',') + '\n}'
            
            prompt += """

Important guidelines:
- Provide concise but informative analysis for each section
- Keep each section to 2-4 sentences
- Be objective and professional in your analysis
- Focus on the research content and methodology
- Ensure all JSON values are properly escaped strings"""
            
        else:
            prompt = "You are an expert research paper analyst. Analyze the given research paper and provide structured diagnostics.\n\n"
            prompt += "Provide analysis for the following sections:\n"
            
            for section in include_sections:
                if section in sections_description:
                    prompt += f"- {section.upper()}: {sections_description[section]}\n"
            
            prompt += "\nFormat your response with clear section headers."
        
        return prompt
    
    def _parse_structured_response(self, response_text: str, include_sections: List[str]) -> Dict[str, str]:
        """
        Parse structured text response when JSON parsing fails
        
        Args:
            response_text: Raw response text
            include_sections: Expected sections
            
        Returns:
            Parsed diagnostics dictionary
        """
        result = {}
        current_section = None
        current_content = []
        
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if line is a section header
            section_found = None
            for section in include_sections:
                if section.upper() in line.upper() and ':' in line:
                    section_found = section
                    break
            
            if section_found:
                # Save previous section
                if current_section and current_content:
                    result[current_section] = ' '.join(current_content).strip()
                
                # Start new section
                current_section = section_found
                current_content = []
                
                # Add content after colon
                colon_index = line.find(':')
                if colon_index != -1 and colon_index < len(line) - 1:
                    content_after_colon = line[colon_index + 1:].strip()
                    if content_after_colon:
                        current_content.append(content_after_colon)
            
            elif current_section and line:
                current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            result[current_section] = ' '.join(current_content).strip()
        
        # Ensure all requested sections are present
        for section in include_sections:
            if section not in result:
                result[section] = "Analysis not available for this section."
        
        return result
    
    async def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text content from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        try:
            # Use PyMuPDF for text extraction (install with: pip install PyMuPDF)
            import fitz  # PyMuPDF
            
            doc = fitz.open(str(pdf_path))
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += page.get_text()
                text_content += "\n\n"  # Add page separator
            
            doc.close()
            
            # Clean up text
            text_content = self._clean_extracted_text(text_content)
            
            return text_content
            
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install PyMuPDF")
            raise Exception("PDF text extraction library not available")
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text content
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text content
        """
        # Remove excessive whitespace
        import re
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n+', '\n\n', text)
        
        # Remove trailing/leading whitespace
        text = text.strip()
        
        return text
    
    async def check_model_availability(self) -> Dict[str, Any]:
        """
        Check if the configured model is available
        
        Returns:
            Model availability status
        """
        try:
            if self.model_type == "openai":
                # Test OpenAI API
                response = await self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=5
                )
                return {
                    "available": True,
                    "model_type": self.model_type,
                    "model_name": self.model_name
                }
            
            else:  # ollama
                import aiohttp
                
                # Test Ollama API
                url = f"{self.ollama_base_url}/api/generate"
                payload = {
                    "model": self.model_name,
                    "prompt": "Test",
                    "stream": False,
                    "options": {"num_predict": 1}
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=10) as response:
                        if response.status == 200:
                            return {
                                "available": True,
                                "model_type": self.model_type,
                                "model_name": self.model_name
                            }
                        else:
                            return {
                                "available": False,
                                "error": f"Ollama returned status {response.status}"
                            }
            
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            return {
                "available": False,
                "error": str(e)
            } 