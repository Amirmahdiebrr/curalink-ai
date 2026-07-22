"""
app/services/reminder_service.py

Daily job (9.2): finds due test-followup reminders across all users
and sends an SMS via the provider-agnostic SMS layer (9.1).
"""

from sqlalchemy.orm import Session

from app.models import User
from app.services.history_service import get_due_reminders_for_all_users
from app.services.sms_service import SMSService


class ReminderService:

    def __init__(self):
        self.sms = SMSService()

    def _build_message(self, test_name: str, person_name: str | None) -> str:
        if person_name:
            return f"یادآوری CuraLink: زمان تکرار آزمایش {test_name} برای {person_name} فرا رسیده است."
        return f"یادآوری CuraLink: زمان تکرار آزمایش {test_name} شما فرا رسیده است."

    async def run(self, db: Session):

        due_items = get_due_reminders_for_all_users(db)

        print(f"[ReminderService] Found {len(due_items)} due reminder(s)", flush=True)

        for item in due_items:

            user = db.query(User).filter(User.id == item.user_id).first()

            if not user or not user.phone:
                print(f"[ReminderService] Skipped test_result_id={item.id}: no phone number on file", flush=True)
                continue

            person_name = item.family_member.name if item.family_member else None
            message = self._build_message(item.test_name, person_name)

            sent = await self.sms.send_reminder(user.phone, message)

            if sent:
                item.followup_reminder_sent = True
                db.commit()
                print(f"[ReminderService] Reminder sent for test_result_id={item.id}", flush=True)