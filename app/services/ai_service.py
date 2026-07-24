from app.services.deepseek import ask_ai, DeepSeekError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AIService:

    async def analyze(self, prompt):

        try:
            return await ask_ai(prompt)

        except DeepSeekError as e:

            logger.error(f"[AIService] DeepSeekError: {e}")

            return f"""
تحلیل AI انجام نشد.

خطا:
{e}
"""

        except Exception as e:

            logger.error(f"[AIService] Unexpected error: {e}")

            return f"""
خطای غیرمنتظره در تحلیل AI.

جزئیات:
{e}
"""