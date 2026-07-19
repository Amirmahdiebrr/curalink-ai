"""
AI Configuration
"""

import os

from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()



@dataclass(frozen=True)
class AISettings:
    """
    AI configuration.
    """

    provider: str

    model: str

    api_key: str

    base_url: str

    timeout: int = 60



    @classmethod
    def load(cls):

        provider = os.getenv(
            "AI_PROVIDER",
            "nvidia",
        ).lower()



        configs = {

            "nvidia": {

                "model":
                    os.getenv(
                        "AI_MODEL",
                        "deepseek-ai/deepseek-v3",
                    ),

                "api_key":
                    os.getenv(
                        "NVIDIA_API_KEY",
                        "",
                    ),

                "base_url":
                    "https://integrate.api.nvidia.com/v1",
            },


            "deepseek": {

                "model":
                    os.getenv(
                        "AI_MODEL",
                        "deepseek-chat",
                    ),

                "api_key":
                    os.getenv(
                        "DEEPSEEK_API_KEY",
                        "",
                    ),

                "base_url":
                    "https://api.deepseek.com",
            },


            "openai": {

                "model":
                    os.getenv(
                        "AI_MODEL",
                        "gpt-4.1",
                    ),

                "api_key":
                    os.getenv(
                        "OPENAI_API_KEY",
                        "",
                    ),

                "base_url":
                    "https://api.openai.com/v1",
            },

        }



        if provider not in configs:

            raise RuntimeError(
                f"Unsupported AI provider: {provider}"
            )



        config = configs[provider]



        return cls(

            provider=provider,

            model=config["model"],

            api_key=config["api_key"],

            base_url=config["base_url"],

            timeout=int(
                os.getenv(
                    "AI_TIMEOUT",
                    "60",
                )
            ),
        )