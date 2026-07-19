"""
app/classifiers/document_classifier.py

Rule-based medical document classifier.

Author:
Medical AI Analyzer
"""

import re


class DocumentClassifier:

    LAB_PATTERNS = [
        r"\bWBC\b",
        r"\bRBC\b",
        r"\bHGB\b",
        r"\bHB\b",
        r"\bHCT\b",
        r"\bMCV\b",
        r"\bMCH\b",
        r"\bPLT\b",
        r"\bPlatelet\b",
        r"\bGlucose\b",
        r"\bTSH\b",
        r"\bCreatinine\b",
    ]


    ULTRASOUND_PATTERNS = [
        r"ultrasound",
        r"sonography",
        r"kidney",
        r"liver",
        r"uterus",
        r"ovary",
        r"fetus",
        r"gallbladder",
        r"spleen",
    ]


    RADIOLOGY_PATTERNS = [
        r"x-ray",
        r"radiology",
        r"ct",
        r"mri",
        r"impression",
        r"findings",
    ]


    PATHOLOGY_PATTERNS = [
        r"biopsy",
        r"histopathology",
        r"microscopic",
        r"gross description",
        r"specimen",
    ]


    @classmethod
    def detect(cls, text: str) -> str:

        text = text.lower()


        if any(
            re.search(pattern, text)
            for pattern in cls.LAB_PATTERNS
        ):
            return "lab_report"


        if any(
            re.search(pattern, text)
            for pattern in cls.ULTRASOUND_PATTERNS
        ):
            return "ultrasound"


        if any(
            re.search(pattern, text)
            for pattern in cls.RADIOLOGY_PATTERNS
        ):
            return "radiology"


        if any(
            re.search(pattern, text)
            for pattern in cls.PATHOLOGY_PATTERNS
        ):
            return "pathology"


        return "lab_report"