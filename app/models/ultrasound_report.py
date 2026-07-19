"""
Ultrasound report model.
"""

from typing import List, Optional

from pydantic import Field

from app.models.base_report import (
    BaseMedicalReport,
    MedicalFinding,
)

from app.models.document_type import DocumentType


class UltrasoundReport(BaseMedicalReport):

    document_type: DocumentType = DocumentType.ULTRASOUND

    examination: Optional[str] = None

    body_region: Optional[str] = None

    patient_name: Optional[str] = None

    patient_age: Optional[str] = None

    patient_gender: Optional[str] = None

    examination_date: Optional[str] = None

    impression: Optional[str] = None

    findings: List[MedicalFinding] = Field(
        default_factory=list
    )

    abnormal: bool = False

    urgency: str = "normal"