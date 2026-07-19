"""
app/services/pdf_service.py

PDF text extraction service.

Responsibilities:
- Read PDF files
- Extract text from all pages
- Handle PDF-related errors

Author:
Medical Lab Analyzer
"""

from __future__ import annotations

from pathlib import Path

from PyPDF2 import PdfReader


class PDFExtractionError(Exception):
    """
    Raised when text extraction from PDF fails.
    """
    pass


class PDFService:
    """
    Service responsible for extracting text from PDF documents.
    """

    @staticmethod
    def extract_text(file_path: Path) -> str:
        """
        Extract text from a PDF file.

        Parameters
        ----------
        file_path : Path
            Path to the PDF file.

        Returns
        -------
        str
            Extracted text.

        Raises
        ------
        PDFExtractionError
            If the file cannot be processed or contains no readable text.
        """

        if not file_path.exists():
            raise PDFExtractionError(
                f"File not found: {file_path}"
            )

        try:
            reader = PdfReader(str(file_path))

            pages_text: list[str] = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pages_text.append(text.strip())

            extracted_text = "\n\n".join(pages_text).strip()

            if not extracted_text:
                raise PDFExtractionError(
                    "No readable text found in the PDF."
                )

            return extracted_text

        except PDFExtractionError:
            raise

        except Exception as exc:
            raise PDFExtractionError(
                f"Failed to process PDF: {exc}"
            ) from exc