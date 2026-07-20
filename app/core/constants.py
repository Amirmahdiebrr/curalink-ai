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


ALLOWED_FILE_EXTENSIONS = [

    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".heic",
    ".heif",

]



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