"""
app/schemas/ai_response.py

AI response schemas.

These schemas define the ONLY valid structure
that AI models are allowed to return.

Author:
Medical AI Analyzer
"""

from typing import Literal

from pydantic import BaseModel, Field


class AIParameter(BaseModel):
    """
    Medical parameter extracted by AI.
    """

    name: str

    value: str | None = None

    unit: str | None = None

    reference_range: str | None = None

    status: Literal[
        "normal",
        "low",
        "high",
        "critical",
        "abnormal",
        "unknown",
    ] = "unknown"

    interpretation: str | None = None



class AIFinding(BaseModel):
    """
    Important medical finding.
    """

    title: str

    description: str

    severity: Literal[
        "info",
        "warning",
        "critical",
    ] = "info"



class AIRecommendation(BaseModel):
    """
    AI recommendation.
    """

    text: str

    priority: Literal[
        "low",
        "normal",
        "high",
        "urgent",
    ] = "normal"



class AIResponse(BaseModel):
    """
    Standard AI output.
    """

    document_type: Literal[
        "lab_report",
        "ultrasound",
        "radiology",
        "pathology",
    ]

    title: str

    summary: str

    confidence: float = Field(
        ge=0,
        le=1,
    )

    findings: list[AIFinding] = Field(
        default_factory=list
    )

    parameters: list[AIParameter] = Field(
        default_factory=list
    )

    recommendations: list[AIRecommendation] = Field(
        default_factory=list
    )