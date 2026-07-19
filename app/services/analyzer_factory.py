"""
app/services/analyzer_factory.py

Analyzer Factory.

Creates analyzers for different
medical document types.

Author:
Medical AI Analyzer
"""

from app.analyzers.medical_analyzer import MedicalAnalyzer


class AnalyzerFactory:
    """
    Factory for medical analyzers.
    """

    _supported_types = {

        "lab_report",

        "ultrasound",

        "radiology",

        "pathology",

    }


    @classmethod
    def get_analyzer(
        cls,
        document_type: str,
    ) -> MedicalAnalyzer:
        """
        Return analyzer instance.
        """

        if document_type not in cls._supported_types:

            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        return MedicalAnalyzer(
            document_type
        )


    @classmethod
    def supported_types(
        cls,
    ) -> list[str]:
        """
        Return supported document types.
        """

        return sorted(
            cls._supported_types
        )