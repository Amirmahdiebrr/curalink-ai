"""
Document Service

This service extracts text from any supported document.

Responsibilities
----------------
- Detect document type
- Extract text from PDF
- Extract text from Image
- Future:
    * OCR fallback for scanned PDFs
"""

from pathlib import Path

from app.services.ocr_service import OCRService
from app.services.pdf_service import PDFService

from app.utils.file_utils import (
    is_image,
    is_pdf,
)


class DocumentServiceError(Exception):
    pass


class DocumentService:

    @staticmethod
    def extract_text(file_path: Path) -> str:
        """
        Extract text from supported documents.
        """

        if is_pdf(file_path):

            return PDFService.extract_text(file_path)

        if is_image(file_path):

            return OCRService.extract_text(file_path)

        raise DocumentServiceError(
            "Unsupported document type."
        )