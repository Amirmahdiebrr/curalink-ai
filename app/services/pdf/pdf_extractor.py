"""
app/services/pdf/pdf_extractor.py

PDF Text Extractor
"""

from io import BytesIO

from fastapi import UploadFile
from PyPDF2 import PdfReader


class PDFExtractor:
    """
    Extract text from PDF documents.
    """

    def extract(
        self,
        file: UploadFile,
    ) -> str:

        pdf_bytes = file.file.read()

        reader = PdfReader(
            BytesIO(pdf_bytes)
        )

        text = ""

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text.strip()