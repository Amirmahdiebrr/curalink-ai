"""
app/models/base_report.py

Base medical report models.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class MedicalParameter(BaseModel):
    """
    Medical measurement parameter.
    """

    name: str

    value: Optional[str] = None

    unit: Optional[str] = None

    reference_range: Optional[str] = None

    status: Optional[str] = None

    interpretation: Optional[str] = None



class MedicalFinding(BaseModel):
    """
    Medical finding extracted from report.
    """

    title: str

    description: str

    severity: str = "info"



class MedicalRecommendation(BaseModel):
    """
    Medical recommendation.
    """

    text: str

    priority: str = "normal"



class BaseMedicalReport(BaseModel):
    """
    Base class for all medical reports.
    """

    document_type: str

    title: str = ""

    summary: str = ""

    confidence: float = 0.0

    findings: List[MedicalFinding] = Field(
        default_factory=list
    )

    parameters: List[MedicalParameter] = Field(
        default_factory=list
    )

    recommendations: List[MedicalRecommendation] = Field(
        default_factory=list
    )

    raw_text: Optional[str] = None