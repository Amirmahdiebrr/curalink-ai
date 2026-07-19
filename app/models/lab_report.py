"""
Laboratory report model.
"""

from typing import List, Optional

from pydantic import Field

from app.models.base_report import (
    BaseMedicalReport,
    MedicalParameter,
)

from app.models.document_type import DocumentType


class LabReport(BaseMedicalReport):

    document_type: DocumentType = DocumentType.LAB_REPORT

    laboratory_name: Optional[str] = None

    report_category: Optional[str] = Field(
        default=None,
        description="CBC, Biochemistry, Hormone..."
    )

    patient_name: Optional[str] = None

    patient_age: Optional[str] = None

    patient_gender: Optional[str] = None

    sample_date: Optional[str] = None

    parameters: List[MedicalParameter] = Field(
        default_factory=list
    )

    overall_status: str = "unknown"