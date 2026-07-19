"""
Base Medical Analyzer
"""

from abc import ABC, abstractmethod



class BaseAnalyzer(ABC):


    def __init__(self):

        from app.services.ai.ai_service import AIService

        self.ai_service = AIService()



    @property
    @abstractmethod
    def document_type(self) -> str:
        pass



    @abstractmethod
    def build_prompt(
        self,
        text: str,
    ) -> str:
        pass



    def analyze(
        self,
        text: str,
    ):


        prompt = self.build_prompt(
            text
        )


        response = self.ai_service.ask(
            prompt
        )


        return response