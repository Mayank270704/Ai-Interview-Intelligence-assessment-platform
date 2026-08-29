"""PDF extraction and text cleaning for resumes."""

import re
from io import BytesIO

from pypdf import PdfReader


class PDFExtractionError(Exception):
    """Error during PDF extraction."""

    pass


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Extracted text from PDF

    Raises:
        PDFExtractionError: If PDF is invalid or unreadable
    """
    if not pdf_bytes:
        raise PDFExtractionError("PDF is empty")

    try:
        pdf_file = BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        if len(reader.pages) == 0:
            raise PDFExtractionError("PDF has no pages")

        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text or not text.strip():
            raise PDFExtractionError("PDF contains no extractable text")

        return text

    except Exception as e:
        if isinstance(e, PDFExtractionError):
            raise
        raise PDFExtractionError(f"Failed to extract text from PDF: {str(e)}")


def clean_resume_text(text: str) -> str:
    """
    Clean and normalize resume text.

    Args:
        text: Raw extracted text from PDF

    Returns:
        Cleaned text
    """
    # Remove multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Remove multiple newlines, but preserve structure
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split("\n")]

    # Remove empty lines but preserve some structure
    lines = [line for line in lines if line]

    # Rejoin with single newline
    text = "\n".join(lines)

    # Remove control characters (except newlines)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()
