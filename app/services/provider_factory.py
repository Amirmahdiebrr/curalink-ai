"""
app/services/provider_factory.py

AI provider factory.
"""

from app.config.ai_settings import AISettings

from app.services.ai.nvidia_provider import NvidiaProvider
from app.services.ai.deepseek_provider import DeepSeekProvider
from app.services.ai.openai_provider import OpenAIProvider



class ProviderFactory:
    """
    Creates AI provider instances.
    """


    @staticmethod
    def create():

        settings = AISettings.load()


        if settings.provider == "nvidia":

            return NvidiaProvider(
                settings
            )


        if settings.provider == "deepseek":

            return DeepSeekProvider(
                settings
            )


        if settings.provider == "openai":

            return OpenAIProvider(
                settings
            )


        raise RuntimeError(
            f"Unsupported AI provider: {settings.provider}"
        )