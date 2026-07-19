from app.prompts.base_prompt import BasePrompt
from app.models.document_type import DocumentType

from app.prompts.templates import (
    SYSTEM_ROLE,
    GENERAL_RULES,
    OUTPUT_RULES,
    DISCLAIMER,
)


class MedicalPrompt(BasePrompt):

    def __init__(
        self,
        document_type: DocumentType,
        instructions: str,
    ):
        self._document_type = document_type
        self.instructions = instructions


    @property
    def document_type(self):
        return self._document_type


    def build(
        self,
        content: str,
    ) -> str:

        return f"""
{SYSTEM_ROLE}

{GENERAL_RULES}

Document Type:
{self.document_type.value}


Specific Instructions:

{self.instructions}


{OUTPUT_RULES}


Medical Document:

{content}


{DISCLAIMER}
"""