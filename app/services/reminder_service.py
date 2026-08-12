"""
app/services/reminder_service.py

Daily job: finds due test-followup reminders و یادآوری‌های پیگیری
ثبت‌شده توسط پزشک (مبتنی بر نوع بیمه‌ی بیمار) و از طریق لایه‌ی
مستقل از پروایدر پیامک ارسال می‌کند.
"""

from sqlalchemy.orm import Session

from app.models import User, INSURANCE_LABELS
from app.services.history_service import get_due_reminders_for_all_users
from app.services.doctor_tools_service import get_due_patient_followups
from app.services.sms_service import SMSService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ReminderService:

    def __init__(self):
        self.sms = SMSService()

    def _build_message(self, test_name: str, person_name: str | None) -> str:
        if person_name:
            return f"یادآوری CuraLink: زمان تکرار آزمایش {test_name} برای {person_name} فرا رسیده است."
        return f"یادآوری CuraLink: زمان تکرار آزمایش {test_name} شما فرا رسیده است."

    def _build_followup_message(self, item) -> str:
        date_str = item.followup_date.strftime("%Y-%m-%d")
        message = f"یادآوری CuraLink: پزشک شما یک نوبت پیگیری برای تاریخ {date_str} برای شما ثبت کرده است."

        if item.note:
            message += f" یادداشت پزشک: {item.note}"

        insurance_label = INSURANCE_LABELS.get(item.insurance_type)
        if insurance_label and item.insurance_type != "none":
            message += f" (بیمه: {insurance_label})"

        return message

    async def run(self, db: Session):

        due_items = get_due_reminders_for_all_users(db)

        logger.info(f"[ReminderService] Found {len(due_items)} due test-followup reminder(s)")

        for item in due_items:

            user = db.query(User).filter(User.id == item.user_id).first()

            if not user or not user.phone:
                logger.info(f"[ReminderService] Skipped test_result_id={item.id}: no phone number on file")
                continue

            person_name = item.family_member.name if item.family_member else None
            message = self._build_message(item.test_name, person_name)

            sent = await self.sms.send_reminder(user.phone, message)

            if sent:
                item.followup_reminder_sent = True
                db.commit()
                logger.info(f"[ReminderService] Reminder sent for test_result_id={item.id}")

        due_followups = get_due_patient_followups(db)

        logger.info(f"[ReminderService] Found {len(due_followups)} due patient-followup reminder(s)")

        for followup in due_followups:

            if not followup.patient_user_id:
                followup.reminder_sent = True
                db.commit()
                continue

            patient = db.query(User).filter(User.id == followup.patient_user_id).first()

            if not patient or not patient.phone:
                logger.info(f"[ReminderService] Skipped followup_id={followup.id}: no phone number on file")
                continue

            message = self._build_followup_message(followup)

            sent = await self.sms.send_reminder(patient.phone, message)

            if sent:
                followup.reminder_sent = True
                db.commit()
                logger.info(f"[ReminderService] Followup reminder sent for followup_id={followup.id}")