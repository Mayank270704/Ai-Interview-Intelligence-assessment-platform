"""Resume processor service - orchestrates the resume analysis pipeline."""

from app.ai.llm.client import LLMClient
from app.ai.resume_intelligence.pdf_processor import (
    extract_text_from_pdf,
    clean_resume_text,
)
from app.schemas.resume import CandidateProfile


class ResumeProcessor:
    """Orchestrates the resume analysis pipeline."""

    def __init__(self):
        """Initialize the resume processor with LLM client."""
        self.llm_client = LLMClient()

    def process_resume(self, pdf_bytes: bytes) -> CandidateProfile:
        """
        Process a resume PDF and extract candidate profile.

        Pipeline:
        1. Extract text from PDF
        2. Clean and normalize text
        3. Send to Gemini for structured analysis
        4. Return validated CandidateProfile

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            CandidateProfile: Structured candidate information

        Raises:
            PDFExtractionError: If PDF extraction fails
            ValueError: If Gemini analysis fails or returns invalid data
        """
        # Step 1: Extract text from PDF
        raw_text = extract_text_from_pdf(pdf_bytes)

        # Step 2: Clean and normalize text
        cleaned_text = clean_resume_text(raw_text)

        # Step 3: Send to Gemini for structured analysis
        prompt = self._build_analysis_prompt(cleaned_text)

        try:
            candidate_profile = self.llm_client.generate_structured(
                prompt, CandidateProfile
            )
            return candidate_profile
        except Exception as e:
            raise ValueError(f"Failed to analyze resume: {str(e)}")

    @staticmethod
    def _build_analysis_prompt(cleaned_text: str) -> str:
        """
        Build the prompt for Gemini to analyze the resume.

        Args:
            cleaned_text: Cleaned resume text

        Returns:
            Formatted prompt for the LLM
        """
        prompt = f"""Analyze the following resume and extract a structured candidate profile.

Resume Text:
---
{cleaned_text}
---

Instructions:
1. Extract all relevant information from the resume
2. For each field, include direct quotes or evidence from the resume
3. For claims (quantitative improvements, technical achievements, etc.), identify and categorize them
4. Do not invent information that is not in the resume
5. Return the data as structured JSON matching the CandidateProfile schema

Focus on:
- Candidate identity (name, email, phone, location)
- Professional summary if available
- Education entries with institution, degree, field
- Skills with proficiency levels
- Technologies and tools used
- Work experience with companies, positions, dates
- Projects with descriptions and technologies
- Certifications and credentials
- Achievements and awards
- Important claims that might be verified in an interview

For each major claim (e.g., "improved accuracy by 18%", "built a BERT system"), capture:
- The exact claim text
- The category (quantitative, technical, or domain)
- The context (what project or role)
- The resume evidence (exact quote)

Return valid JSON that matches the CandidateProfile schema."""
        return prompt
