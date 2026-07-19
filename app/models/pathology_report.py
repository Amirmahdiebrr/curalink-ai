"""
Pathology report model.
"""

from typing import List, Optional

from pydantic import Field

from app.models.base_report import (
    BaseMedicalReport,
    MedicalFinding,
)

from app.models.document_type import DocumentType


class PathologyReport(BaseMedicalReport):

    document_type: DocumentType = DocumentType.PATHOLOGY

    specimen: Optional[str] = None

    specimen_site: Optional[str] = None

    diagnosis: Optional[str] = None

    microscopic_description: Optional[str] = None

    gross_description: Optional[str] = None

    findings: List[MedicalFinding] = Field(
        default_factory=list
    )

    malignancy: bool = False

    stage: Optional[str] = None

    grade: Optional[str] = None

    recommendation: Optional[str] = None