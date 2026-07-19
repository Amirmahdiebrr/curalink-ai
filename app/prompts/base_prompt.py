from abc import ABC, abstractmethod

from app.models.document_type import DocumentType


class BasePrompt(ABC):

    @property
    @abstractmethod
    def document_type(self) -> DocumentType:
        pass


    @abstractmethod
    def build(
        self,
        content: str,
    ) -> str:
        pass