"""
app/services/diet_service.py
"""

from sqlalchemy.orm import Session

from app.prompts.diet_prompt import DIET_PROMPT_TEMPLATE
from app.services.ai_service import AIService
from app.services.history_service import get_latest_results_by_test
from app.services.diet_history_service import get_latest_diet_plan_for_person
from app.core.health_profile import build_health_profile_text


NO_RESULTS_TEXT = "هیچ نتیجه آزمایش عددی‌ای برای این فرد ثبت نشده است."
NO_CONTEXT_TEXT = "کاربر شرایط خاصی وارد نکرده است."
NO_PREVIOUS_PLAN_TEXT = "این اولین برنامه‌ی غذایی این فرد است."
MAX_CONTEXT_LENGTH = 800
MAX_PREVIOUS_PLAN_LENGTH = 2500


class DietService:

    def __init__(self):
        self.ai = AIService()

    def _build_test_summary(self, results: list) -> str:
        if not results:
            return NO_RESULTS_TEXT

        lines = []

        for r in results:
            status_label = {"high": "بالا", "low": "پایین", "normal": "طبیعی"}.get(r.status, r.status or "نامشخص")
            line = f"- {r.test_name}: {r.value_text} {r.unit or ''} (بازه مرجع: {r.reference_range or 'نامشخص'}) — وضعیت: {status_label}"
            lines.append(line)

        return "\n".join(lines)

    def _prepare_context(self, extra_context: str | None) -> str:
        if not extra_context:
            return NO_CONTEXT_TEXT

        cleaned = extra_context.strip()

        if not cleaned:
            return NO_CONTEXT_TEXT

        return cleaned[:MAX_CONTEXT_LENGTH]

    def _build_previous_plan_text(self, db: Session, user_id: int, family_member_id: int | None) -> str:
        previous = get_latest_diet_plan_for_person(db, user_id, family_member_id)

        if not previous or not previous.plan_text:
            return NO_PREVIOUS_PLAN_TEXT

        header = f"تاریخ برنامه قبلی: {previous.created_at.strftime('%Y-%m-%d')}"
        if previous.context:
            header += f" | شرایط ثبت‌شده قبلی: {previous.context[:300]}"

        body = previous.plan_text.strip()[:MAX_PREVIOUS_PLAN_LENGTH]

        return f"{header}\n\nمتن برنامه‌ی قبلی:\n{body}"

    async def generate(
        self,
        db: Session,
        user_id: int,
        family_member_id: int | None,
        health_profile_fields: dict,
        extra_context: str | None = None,
    ) -> str:

        results = get_latest_results_by_test(db, user_id, family_member_id)

        patient_profile = build_health_profile_text(health_profile_fields)
        test_summary = self._build_test_summary(results)
        context_display = self._prepare_context(extra_context)
        previous_plan_text = self._build_previous_plan_text(db, user_id, family_member_id)

        prompt = DIET_PROMPT_TEMPLATE.format(
            patient_profile=patient_profile,
            extra_context=context_display,
            test_summary=test_summary,
            previous_plan=previous_plan_text,
        )

        return await self.ai.analyze(prompt)