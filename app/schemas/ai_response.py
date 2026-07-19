"""
app/schemas/ai_response.py

Validated AI output schema.
"""

from typing import Literal

from pydantic import BaseModel, Field



class AIParameter(BaseModel):

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

    title: str

    description: str

    severity: Literal[
        "info",
        "warning",
        "critical",
    ] = "info"



class AIRecommendation(BaseModel):

    text: str

    priority: Literal[
        "low",
        "normal",
        "high",
        "urgent",
    ] = "normal"



class AIResponse(BaseModel):

    document_type: Literal[
        "lab_report",
        "ultrasound",
        "radiology",
        "pathology",
    ]

    title: str = "Medical Report"

    summary: str

    confidence: float = Field(
        default=0.0,
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