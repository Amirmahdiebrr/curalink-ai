from app.models.document_type import DocumentType

from app.prompts.lab_prompt import LabPrompt
from app.prompts.radiology_prompt import RadiologyPrompt
from app.prompts.ultrasound_prompt import UltrasoundPrompt
from app.prompts.pathology_prompt import PathologyPrompt


class PromptFactory:

    prompts = {

        DocumentType.LAB_REPORT: LabPrompt(),

        DocumentType.RADIOLOGY: RadiologyPrompt(),

        DocumentType.ULTRASOUND: UltrasoundPrompt(),

        DocumentType.PATHOLOGY: PathologyPrompt(),

    }


    @classmethod
    def create(
        cls,
        document_type: DocumentType,
        content: str,
    ) -> str:


        prompt = cls.prompts.get(
            document_type
        )


        if not prompt:
            raise ValueError(
                f"Unsupported document type: {document_type}"
            )


        return prompt.build(content)