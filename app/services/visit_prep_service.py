"""
app/services/visit_prep_service.py

Builds a doctor-visit preparation summary from a person's aggregated
latest lab results and an optional visit reason provided by the user.
"""

from sqlalchemy.orm import Session

from app.prompts.visit_prep_prompt import VISIT_PREP_PROMPT_TEMPLATE
from app.services.ai_service import AIService
from app.services.history_service import get_latest_results_by_test


GENDER_LABELS = {
    "male": "مرد",
    "female": "زن",
    "other": "سایر",
}

NO_PROFILE_TEXT = "اطلاعاتی از سن/جنسیت این فرد در دسترس نیست."

NO_RESULTS_TEXT = "هیچ نتیجه آزمایش عددی‌ای برای این فرد ثبت نشده است."

NO_REASON_TEXT = "کاربر دلیل یا شرح خاصی برای این مراجعه وارد نکرده است."

MAX_REASON_LENGTH = 800


class VisitPrepService:

    def __init__(self):
        self.ai = AIService()

    def _build_patient_profile(self, age: int | None, gender: str | None) -> str:
        parts = []

        if age is not None:
            parts.append(f"سن: {age} سال")

        if gender:
            gender_label = GENDER_LABELS.get(gender)
            if gender_label:
                parts.append(f"جنسیت: {gender_label}")

        if not parts:
            return NO_PROFILE_TEXT

        return " | ".join(parts)

    def _build_test_summary(self, results: list) -> str:
        if not results:
            return NO_RESULTS_TEXT

        lines = []

        for r in results:
            status_label = {"high": "بالا", "low": "پایین", "normal": "طبیعی"}.get(r.status, r.status or "نامشخص")
            line = f"- {r.test_name}: {r.value_text} {r.unit or ''} (بازه مرجع: {r.reference_range or 'نامشخص'}) — وضعیت: {status_label}"
            lines.append(line)

        return "\n".join(lines)

    def _prepare_reason(self, visit_reason: str | None) -> str:
        if not visit_reason:
            return NO_REASON_TEXT

        cleaned = visit_reason.strip()

        if not cleaned:
            return NO_REASON_TEXT

        return cleaned[:MAX_REASON_LENGTH]

    async def generate(
        self,
        db: Session,
        user_id: int,
        family_member_id: int | None,
        age: int | None,
        gender: str | None,
        visit_reason: str | None = None,
    ) -> str:

        results = get_latest_results_by_test(db, user_id, family_member_id)

        patient_profile = self._build_patient_profile(age, gender)
        test_summary = self._build_test_summary(results)
        reason_display = self._prepare_reason(visit_reason)

        prompt = VISIT_PREP_PROMPT_TEMPLATE.format(
            patient_profile=patient_profile,
            visit_reason=reason_display,
            test_summary=test_summary,
        )

        return await self.ai.analyze(prompt)