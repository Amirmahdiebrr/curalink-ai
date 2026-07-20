"""
app/services/chat_service.py

Handles the medical Q&A chat that lets a user ask follow-up
questions about an already-generated analysis report.
"""

from app.prompts.chat_prompt import CHAT_SYSTEM_PROMPT
from app.services.deepseek import ask_ai, DeepSeekError


REFERRAL_TEXT = "\n\nبرای بررسی دقیق‌تر می‌توانید با مجموعه‌ی ما تماس بگیرید تا پزشکان ما شما را راهنمایی کنند."


class ChatService:

    def _format_history(self, history: list[dict]) -> str:

        if not history:
            return "بدون مکالمه‌ی قبلی."

        lines = []

        for turn in history[-6:]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()

            if not content:
                continue

            speaker = "کاربر" if role == "user" else "دستیار"
            lines.append(f"{speaker}: {content}")

        return "\n".join(lines) if lines else "بدون مکالمه‌ی قبلی."

    def _build_prompt(self, report_context: str, history: list[dict], question: str) -> str:

        history_text = self._format_history(history)

        return f"""
{CHAT_SYSTEM_PROMPT}

--- گزارش آزمایش کاربر ---
{report_context[:6000]}

--- مکالمه‌ی قبلی ---
{history_text}

--- سوال جدید کاربر ---
{question.strip()}
"""

    def _is_off_topic_refusal(self, answer: str) -> bool:
        refusal_markers = [
            "فقط می‌توانم",
            "فقط می توانم",
            "خارج از حوزه",
            "بی‌ربط",
            "مرتبط با آزمایش",
        ]
        return any(marker in answer for marker in refusal_markers)

    async def ask(self, report_context: str, history: list[dict], question: str) -> str:

        prompt = self._build_prompt(report_context, history, question)

        try:
            answer = await ask_ai(prompt)
        except DeepSeekError as e:
            print(f"[Chat] DeepSeekError: {e}", flush=True)
            raise

        answer = answer.strip()

        if not self._is_off_topic_refusal(answer):
            answer += REFERRAL_TEXT

        return answer