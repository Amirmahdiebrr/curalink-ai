"""
app/services/workout_service.py
"""

from sqlalchemy.orm import Session

from app.prompts.workout_prompt import WORKOUT_PROMPT_TEMPLATE
from app.services.ai_service import AIService
from app.services.history_service import get_latest_results_by_test
from app.services.workout_history_service import get_latest_workout_plan_for_person
from app.core.health_profile import build_health_profile_text


NO_RESULTS_TEXT = "هیچ نتیجه آزمایش عددی‌ای برای این فرد ثبت نشده است."
NO_INJURIES_TEXT = "کاربر محدودیت یا آسیب خاصی وارد نکرده است."
NO_PREVIOUS_PLAN_TEXT = "این اولین برنامه‌ی تمرینی این فرد است."
MAX_INJURIES_LENGTH = 800
MAX_PREVIOUS_PLAN_LENGTH = 2500

GOAL_LABELS = {
    "fat_loss": "کاهش چربی بدن",
    "muscle_gain": "افزایش حجم و قدرت عضلانی",
    "general_fitness": "تناسب اندام و سلامت عمومی",
    "endurance": "افزایش استقامت قلبی‌عروقی",
    "rehab": "بازتوانی / بازگشت ملایم به ورزش",
}

FITNESS_LEVEL_LABELS = {
    "beginner": "مبتدی",
    "intermediate": "متوسط",
    "advanced": "پیشرفته",
}

EQUIPMENT_LABELS = {
    "none": "بدون وسیله (تمرین با وزن بدن)",
    "home_basic": "وسایل ساده خانگی (دمبل/کش تمرینی)",
    "full_gym": "دسترسی کامل به باشگاه",
}


class WorkoutService:

    def __init__(self):
        self.ai = AIService()

    def _build_test_summary(self, results: list) -> str:
        if not results:
            return NO_RESULTS_TEXT

        lines = []
        for r in results:
            status_label = {"high": "بالا", "low": "پایین", "normal": "طبیعی"}.get(r.status, r.status or "نامشخص")
            lines.append(f"- {r.test_name}: {r.value_text} {r.unit or ''} (بازه مرجع: {r.reference_range or 'نامشخص'}) — وضعیت: {status_label}")

        return "\n".join(lines)

    def _prepare_injuries(self, injuries: str | None) -> str:
        if not injuries:
            return NO_INJURIES_TEXT
        cleaned = injuries.strip()
        if not cleaned:
            return NO_INJURIES_TEXT
        return cleaned[:MAX_INJURIES_LENGTH]

    def _build_previous_plan_text(self, db: Session, user_id: int, family_member_id: int | None) -> str:
        previous = get_latest_workout_plan_for_person(db, user_id, family_member_id)

        if not previous or not previous.plan_text:
            return NO_PREVIOUS_PLAN_TEXT

        goal_label = GOAL_LABELS.get(previous.goal, previous.goal or "نامشخص")
        fitness_label = FITNESS_LEVEL_LABELS.get(previous.fitness_level, previous.fitness_level or "نامشخص")
        equipment_label = EQUIPMENT_LABELS.get(previous.equipment, previous.equipment or "نامشخص")

        header = (
            f"تاریخ برنامه قبلی: {previous.created_at.strftime('%Y-%m-%d')} | "
            f"هدف قبلی: {goal_label} | سطح قبلی: {fitness_label} | "
            f"روزهای قبلی در هفته: {previous.days_per_week or 'نامشخص'} | "
            f"امکانات قبلی: {equipment_label}"
        )

        body = previous.plan_text.strip()[:MAX_PREVIOUS_PLAN_LENGTH]

        return f"{header}\n\nمتن برنامه‌ی قبلی:\n{body}"

    async def generate(
        self,
        db: Session,
        user_id: int,
        family_member_id: int | None,
        health_profile_fields: dict,
        goal: str | None,
        fitness_level: str | None,
        days_per_week: int | None,
        equipment: str | None,
        injuries: str | None = None,
    ) -> str:

        results = get_latest_results_by_test(db, user_id, family_member_id)

        health_profile_text = build_health_profile_text(health_profile_fields)
        test_summary = self._build_test_summary(results)
        injuries_display = self._prepare_injuries(injuries)
        previous_plan_text = self._build_previous_plan_text(db, user_id, family_member_id)

        goal_label = GOAL_LABELS.get(goal, GOAL_LABELS["general_fitness"])
        fitness_level_label = FITNESS_LEVEL_LABELS.get(fitness_level, FITNESS_LEVEL_LABELS["beginner"])
        equipment_label = EQUIPMENT_LABELS.get(equipment, EQUIPMENT_LABELS["none"])
        days_display = days_per_week if days_per_week and 1 <= days_per_week <= 7 else 3

        prompt = WORKOUT_PROMPT_TEMPLATE.format(
            health_profile=health_profile_text,
            test_summary=test_summary,
            goal_label=goal_label,
            fitness_level_label=fitness_level_label,
            equipment_label=equipment_label,
            days_per_week=days_display,
            injuries=injuries_display,
            previous_plan=previous_plan_text,
        )

        return await self.ai.analyze(prompt)