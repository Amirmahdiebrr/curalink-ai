"""
app/models/document_type.py

Medical document type definitions.

Defines all supported medical document categories.

Author:
Medical AI Analyzer
"""

from enum import Enum


class DocumentType(str, Enum):
    """
    Supported medical document types.
    """

    LAB_REPORT = "lab_report"

    ULTRASOUND = "ultrasound"

    RADIOLOGY = "radiology"

    PATHOLOGY = "pathology"