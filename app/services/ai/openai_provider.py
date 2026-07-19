"""
OpenAI Provider
"""

from time import perf_counter

from openai import OpenAI

from app.config.ai_settings import AISettings
from app.models.ai_response import AIResponse
from app.services.ai.base_provider import BaseProvider


class OpenAIProvider(BaseProvider):

    def __init__(
        self,
        settings: AISettings,
    ):

        self.settings = settings

        if not self.settings.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing."
            )

        self.client = OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
        )


    @property
    def provider_name(self):

        return "openai"


    @property
    def model_name(self):

        return self.settings.model


    def ask(
        self,
        prompt: str,
    ) -> AIResponse:

        start = perf_counter()

        response = self.client.chat.completions.create(

            model=self.settings.model,

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            temperature=0.1,

            max_tokens=16384,

            stream=False,
        )

        latency = perf_counter() - start

        usage = response.usage

        return AIResponse(

            text=response.choices[0].message.content,

            provider=self.provider_name,

            model=self.model_name,

            prompt_tokens=getattr(
                usage,
                "prompt_tokens",
                None,
            ),

            completion_tokens=getattr(
                usage,
                "completion_tokens",
                None,
            ),

            total_tokens=getattr(
                usage,
                "total_tokens",
                None,
            ),

            latency=latency,

            finish_reason=response.choices[0].finish_reason,
        )