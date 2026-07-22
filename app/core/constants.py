"""
app/core/constants.py

Application constants.

Author:
Medical AI Analyzer
"""


# ==========================
# File Settings
# ==========================


MAX_UPLOAD_SIZE_MB = 20

# فقط فرمت‌هایی که OCR (Nemotron) واقعاً پشتیبانی می‌کند مجاز هستند.
# tiff/bmp قبلاً اینجا مجاز بودند ولی ocr_service از آن‌ها پشتیبانی
# نمی‌کرد و آپلود بعد از قبول‌شدن با شکست مواجه می‌شد.
ALLOWED_FILE_EXTENSIONS = [

    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",

]

MAX_FILES_PER_REQUEST = 10
MAX_TOTAL_UPLOAD_SIZE_MB = 60
MAX_PDF_PAGES = 20



# ==========================
# Medical Document Types
# ==========================


DOCUMENT_TYPES = {

    "lab_report": "Laboratory Report",

    "ultrasound": "Ultrasound",

    "radiology": "Radiology",

    "pathology": "Pathology",

}



# ==========================
# AI Settings
# ==========================


AI_RESPONSE_LANGUAGE = "Persian"


AI_OUTPUT_FORMAT = "JSON"



# ==========================
# Upload Messages
# ==========================


EMPTY_DOCUMENT_MESSAGE = (
    "Uploaded medical document is empty."
)


UNSUPPORTED_DOCUMENT_MESSAGE = (
    "This medical document type is not supported yet."
)