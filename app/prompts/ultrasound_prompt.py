from app.prompts.medical_prompt import MedicalPrompt
from app.models.document_type import DocumentType


class UltrasoundPrompt(MedicalPrompt):

    def __init__(self):

        super().__init__(
            document_type=DocumentType.ULTRASOUND,

            instructions="""
Analyze ultrasound reports.

Focus on:
- organs examined
- findings
- abnormalities
- clinical importance
- follow-up suggestions

Avoid definitive diagnosis.
"""
        )