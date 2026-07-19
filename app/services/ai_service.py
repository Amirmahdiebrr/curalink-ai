from app.services.deepseek import ask_ai, DeepSeekError


class AIService:

    async def analyze(self, prompt):

        try:
            return await ask_ai(prompt)

        except DeepSeekError as e:

            print("[AIService] DeepSeekError:", e)

            return f"""
تحلیل AI انجام نشد.

خطا:
{e}
"""

        except Exception as e:

            print("[AIService] Unexpected error:", e)

            return f"""
خطای غیرمنتظره در تحلیل AI.

جزئیات:
{e}
"""