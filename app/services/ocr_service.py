"""
app/services/ocr_service.py

Text extraction (OCR) service. Extracts raw text from uploaded
medical document files (PDF or image: PNG/JPG/HEIC/HEIF) so the
extracted text can be passed to the AI for medical interpretation.
"""

import os
import shutil
from pathlib import Path

import pytesseract
from PIL import Image
import pillow_heif
from PyPDF2 import PdfReader
import fitz

from app.core.constants import MAX_PDF_PAGES
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ==========================
# مسیر Tesseract
#
# قبلاً این مسیر هاردکد شده بود روی ویندوز:
#   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# که باعث می‌شد روی لینوکس/Docker (production) کل OCR بشکنه.
#
# منطق جدید:
# 1) اگه TESSERACT_CMD در .env ست شده بود، همون استفاده می‌شه (برای
#    هر سیستم‌عاملی، از جمله ویندوز در محیط توسعه).
# 2) در غیر این صورت، مسیر پیش‌فرض سیستم (PATH) استفاده می‌شه که
#    روی لینوکس/Docker معمولاً همون "tesseract" کافیه.
# ==========================

_TESSERACT_CMD_OVERRIDE = os.getenv("TESSERACT_CMD")

if _TESSERACT_CMD_OVERRIDE:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD_OVERRIDE
    logger.info(f"[OCRService] Using TESSERACT_CMD from env: {_TESSERACT_CMD_OVERRIDE}")
elif shutil.which("tesseract"):
    # از PATH پیدا شد (حالت معمول در لینوکس/Docker)
    logger.info("[OCRService] Using system 'tesseract' found in PATH.")
else:
    logger.warning(
        "[OCRService] دستور 'tesseract' در PATH سیستم پیدا نشد و "
        "TESSERACT_CMD هم در .env تنظیم نشده است. OCR تصویری (برای "
        "تصاویر یا PDFهای اسکن‌شده) کار نخواهد کرد تا زمانی که "
        "Tesseract نصب شود یا مسیر آن در .env مشخص شود."
    )

pillow_heif.register_heif_opener()


class OCRServiceError(Exception):
    pass


class OCRService:
    """
    Extracts raw text from an uploaded medical document file,
    regardless of exam type. PDFs are first tried as text-based
    (fast path); if no text layer exists (scanned document), pages
    are rasterized and run through image OCR instead.
    """

    async def extract(self, filepath: Path) -> str:
        extension = filepath.suffix.lower()

        if extension == ".pdf":
            return await self._extract_from_pdf(filepath)

        return await self._extract_from_image(filepath)

    async def _extract_from_pdf(self, filepath: Path) -> str:
        try:
            reader = PdfReader(str(filepath))
            pages_text = []

            for page in reader.pages[:MAX_PDF_PAGES]:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())

            extracted = "\n\n".join(pages_text).strip()

            if extracted:
                return extracted

        except Exception as e:
            logger.warning(f"[OCRService] PyPDF2 text extraction failed for {filepath}: {e}")

        # اگر PDF متن قابل استخراج نداشت (یعنی اسکن‌شده است)، صفحات را
        # به تصویر تبدیل و روی هرکدام OCR تصویری اجرا می‌کنیم.
        return await self._ocr_scanned_pdf(filepath)

    async def _ocr_scanned_pdf(self, filepath: Path) -> str:
        try:
            doc = fitz.open(str(filepath))
        except Exception as e:
            raise OCRServiceError(f"باز کردن PDF برای OCR تصویری ناموفق بود: {e}")

        pages_text = []

        try:
            page_count = min(len(doc), MAX_PDF_PAGES)

            for page_index in range(page_count):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(dpi=200)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                page_text = pytesseract.image_to_string(image, lang="fas+eng")

                if page_text and page_text.strip():
                    pages_text.append(page_text.strip())
        except Exception as e:
            raise OCRServiceError(f"OCR تصویری روی PDF ناموفق بود (Tesseract نصب/در دسترس است؟): {e}")
        finally:
            doc.close()

        extracted = "\n\n".join(pages_text).strip()

        if not extracted:
            raise OCRServiceError("هیچ متنی از این PDF (حتی به‌صورت اسکن‌شده) استخراج نشد.")

        return extracted

    async def _extract_from_image(self, filepath: Path) -> str:
        try:
            image = Image.open(filepath)
            image = image.convert("RGB")
        except Exception as e:
            raise OCRServiceError(f"باز کردن فایل تصویر ناموفق بود: {e}")

        try:
            text = pytesseract.image_to_string(image, lang="fas+eng")
        except Exception as e:
            raise OCRServiceError(f"OCR روی تصویر ناموفق بود (Tesseract نصب/در دسترس است؟): {e}")

        cleaned = (text or "").strip()

        if not cleaned:
            raise OCRServiceError("هیچ متنی از این تصویر استخراج نشد.")

        return cleaned