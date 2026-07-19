"""
Ultrasound Analyzer
"""

from app.analyzers.base import BaseAnalyzer

from app.prompts.prompt_factory import PromptFactory



class UltrasoundAnalyzer(BaseAnalyzer):


    @property
    def document_type(self):

        return "ultrasound"



    def build_prompt(
        self,
        text: str,
    ):


        return PromptFactory.create(
            document_type=self.document_type,
            content=text,
        )