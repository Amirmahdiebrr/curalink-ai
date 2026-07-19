"""
app/analyzers/analyzer_factory.py

Analyzer factory.
"""

from app.analyzers.lab_analyzer import LabAnalyzer
from app.analyzers.pathology_analyzer import PathologyAnalyzer
from app.analyzers.radiology_analyzer import RadiologyAnalyzer
from app.analyzers.ultrasound_analyzer import UltrasoundAnalyzer

from app.models.document_type import DocumentType


class AnalyzerFactory:
    """
    Factory for medical analyzers.
    """

    _analyzers = {

        DocumentType.LAB_REPORT: LabAnalyzer,

        DocumentType.RADIOLOGY: RadiologyAnalyzer,

        DocumentType.ULTRASOUND: UltrasoundAnalyzer,

        DocumentType.PATHOLOGY: PathologyAnalyzer,

    }

    @classmethod
    def create(
        cls,
        document_type: DocumentType,
    ):

        analyzer = cls._analyzers.get(
            document_type
        )

        if analyzer is None:

            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        return analyzer()