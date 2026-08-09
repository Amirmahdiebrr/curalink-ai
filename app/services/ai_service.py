"""
app/services/ai_service.py
"""

from app.services.deepseek import ask_ai, DeepSeekError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AIService:

    async def analyze(self, prompt: str) -> str:
        """
        Runs the prompt through the AI model and returns the raw text
        response. On failure, raises DeepSeekError instead of returning
        an error message as if it were a successful analysis — callers
        (report/diet/workout/visit-prep services) must catch this and
        fail the job/request properly instead of persisting a fake
        "result".
        """
        try:
            return await ask_ai(prompt)

        except DeepSeekError:
            raise

        except Exception as e:
            logger.error(f"[AIService] Unexpected error: {e}")
            raise DeepSeekError(f"خطای غیرمنتظره در تحلیل AI: {e}") from e