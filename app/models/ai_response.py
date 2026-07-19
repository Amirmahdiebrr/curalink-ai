"""
app/models/ai_response.py

Standard AI response model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AIResponse:
    """
    Unified response returned by AI providers.
    """

    text: str

    provider: str

    model: str

    prompt_tokens: Optional[int] = None

    completion_tokens: Optional[int] = None

    total_tokens: Optional[int] = None

    latency: Optional[float] = None

    finish_reason: Optional[str] = None