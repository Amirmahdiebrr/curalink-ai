"""
app/schemas/parser.py

AI Response Parser.

Responsibilities:
- Validate AI JSON response
- Convert AI output to medical domain models
"""

from app.schemas.ai_response import AIResponse

from app.models.lab_report import LabReport
from app.models.ultrasound_report import UltrasoundReport
from app.models.radiology_report import RadiologyReport
from app.models.pathology_report import PathologyReport


class AIResponseParser:
    """
    Converts validated AI responses
    into medical report models.
    """

    MODEL_MAP = {
        "lab_report": LabReport,
        "ultrasound": UltrasoundReport,
        "radiology": RadiologyReport,
        "pathology": PathologyReport,
    }


    @classmethod
    def parse(
        cls,
        data: dict,
    ):

        # Validate AI JSON structure
        validated = AIResponse.model_validate(
            data
        )


        model_class = cls.MODEL_MAP.get(
            validated.document_type
        )


        if not model_class:

            raise ValueError(
                f"Unsupported document type: {validated.document_type}"
            )


        # Convert schema object to domain model

        return model_class.model_validate(
            validated.model_dump()
        )