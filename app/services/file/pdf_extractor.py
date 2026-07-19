"""
app/services/pdf/pdf_extractor.py

PDF text extraction service.
"""

from fastapi import UploadFile

from io import BytesIO

from PyPDF2 import PdfReader

from app.services.file.ocr_service import OCRService



class PDFExtractor:
    """
    Extract text from PDF documents.
    """


    def __init__(self):

        self.ocr_service = OCRService()



    def extract(
        self,
        file: UploadFile,
    ) -> str:
        """
        Extract text from PDF.

        First tries normal text extraction.
        If PDF is scanned, OCR will be used.
        """


        pdf_bytes = file.file.read()


        reader = PdfReader(
            BytesIO(pdf_bytes)
        )


        text = ""


        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"



        if text.strip():

            return text



        # scanned PDF fallback
        return self._extract_with_ocr(
            pdf_bytes
        )



    def _extract_with_ocr(
        self,
        pdf_bytes: bytes,
    ) -> str:
        """
        OCR fallback for scanned PDFs.
        """

        # placeholder
        # PDF to image conversion will be added here

        return ""