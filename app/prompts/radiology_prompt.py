from app.prompts.medical_prompt import MedicalPrompt
from app.models.document_type import DocumentType


class RadiologyPrompt(MedicalPrompt):

    def __init__(self):

        super().__init__(
            document_type=DocumentType.RADIOLOGY,

            instructions="""
Analyze radiology reports.

Focus on:
- findings
- impression
- important abnormalities
- possible interpretations
- recommended follow-up

Avoid definitive diagnosis.
"""
        )