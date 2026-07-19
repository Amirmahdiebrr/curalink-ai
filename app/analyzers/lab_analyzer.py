"""
app/analyzers/lab_analyzer.py

Laboratory report analyzer.
"""

from app.analyzers.base import BaseAnalyzer
from app.models.document_type import DocumentType


class LabAnalyzer(BaseAnalyzer):
    """
    Analyzer for laboratory reports.
    """

    @property
    def document_type(self) -> DocumentType:
        return DocumentType.LAB_REPORT


    def analyze(
        self,
        extracted_text: str,
    ) -> dict:
        """
        Analyze laboratory report.

        AI processing will be connected later.
        """

        return {
            "document_type": self.document_type.value,
            "raw_text": extracted_text,
        }