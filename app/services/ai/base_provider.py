"""
Base AI Provider.
"""

from abc import ABC, abstractmethod

from app.models.ai_response import AIResponse



class BaseProvider(ABC):
    """
    Interface for AI providers.
    """


    @property
    @abstractmethod
    def provider_name(
        self
    ) -> str:
        pass



    @property
    @abstractmethod
    def model_name(
        self
    ) -> str:
        pass



    @abstractmethod
    def ask(
        self,
        prompt: str,
    ) -> AIResponse:
        pass