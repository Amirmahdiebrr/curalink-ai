from app.prompts.medical_prompt import MedicalPrompt
from app.models.document_type import DocumentType


class PathologyPrompt(MedicalPrompt):

    def __init__(self):

        super().__init__(
            document_type=DocumentType.PATHOLOGY,

            instructions="""
Analyze pathology reports.

Focus on:
- specimen
- diagnosis description
- microscopic findings
- malignancy indicators
- staging information

Avoid definitive clinical decisions.
"""
        )