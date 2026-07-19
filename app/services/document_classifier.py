"""
app/services/document_classifier.py

Classifies medical documents based on extracted text.

Supported document types:
- Laboratory reports
- Ultrasound reports
- Radiology reports
- MRI reports
- CT scan reports
- Prescriptions

This service only classifies documents.
It does not analyze medical content.

Author:
Medical Lab Analyzer
"""

from enum import Enum

from typing import Dict, List


class DocumentType(str, Enum):
    """
    Supported medical document categories.
    """

    LAB_REPORT = "lab_report"

    ULTRASOUND = "ultrasound"

    RADIOLOGY = "radiology"

    MRI = "mri"

    CT_SCAN = "ct_scan"

    PRESCRIPTION = "prescription"

    UNKNOWN = "unknown"


class DocumentClassifier:
    """
    Detect medical document type from extracted text.
    """


    KEYWORDS: Dict[DocumentType, List[str]] = {

        DocumentType.LAB_REPORT: [
            "hemoglobin",
            "hgb",
            "hb",
            "wbc",
            "rbc",
            "platelet",
            "glucose",
            "creatinine",
            "cholesterol",
            "triglyceride",
            "cbc",
            "blood",
            "serum",
        ],


        DocumentType.ULTRASOUND: [
            "ultrasound",
            "sonography",
            "sonography report",
            "abdomen",
            "pelvis",
            "liver",
            "kidney",
            "gallbladder",
            "echo",
        ],


        DocumentType.RADIOLOGY: [
            "x-ray",
            "xray",
            "radiograph",
            "radiography",
            "chest",
            "lung",
            "bone",
            "fracture",
        ],


        DocumentType.MRI: [
            "mri",
            "magnetic resonance",
            "brain",
            "spine",
            "vertebra",
        ],


        DocumentType.CT_SCAN: [
            "ct scan",
            "computed tomography",
            "tomography",
        ],


        DocumentType.PRESCRIPTION: [
            "tablet",
            "capsule",
            "syrup",
            "take",
            "dose",
            "mg",
            "prescription",
        ],
    }


    @classmethod
    def classify(cls, text: str) -> DocumentType:
        """
        Classify document by extracted text.

        Parameters
        ----------
        text:
            OCR/PDF extracted text

        Returns
        -------
        DocumentType
        """

        if not text:
            return DocumentType.UNKNOWN


        normalized_text = text.lower()


        scores = {}


        for document_type, keywords in cls.KEYWORDS.items():

            score = 0

            for keyword in keywords:

                if keyword.lower() in normalized_text:
                    score += 1


            scores[document_type] = score


        best_match = max(
            scores,
            key=scores.get
        )


        if scores[best_match] == 0:
            return DocumentType.UNKNOWN


        return best_match