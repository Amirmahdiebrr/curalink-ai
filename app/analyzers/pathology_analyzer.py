"""
app/analyzers/pathology_analyzer.py
"""

from app.analyzers.base import BaseAnalyzer
from app.prompts.prompt_factory import PromptFactory
from app.services.ai.ai_service import AIService
from app.services.ai.json_parser import AIJsonParser


class PathologyAnalyzer(BaseAnalyzer):

    def __init__(self):

        self.ai = AIService()

    @property
    def document_type(self) -> str:

        return "pathology"

    def analyze(
        self,
        extracted_text: str,
    ):

        prompt = PromptFactory.create(
            self.document_type,
            extracted_text,
        )

        response = self.ai.ask(
            prompt
        )

        return AIJsonParser.parse(
            response.text
        )