"""
app/services/email_service.py

Provider-agnostic email sending layer، به همان الگوی sms_service.py.
فعلاً فقط provider کنسولی (لاگ) وجود دارد؛ بعداً provider واقعی
(SMTP/Mailgun/Zoho) اضافه می‌شود.
"""

from __future__ import annotations

from app.config import EMAIL_PROVIDER, APP_BASE_URL
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EmailError(Exception):
    pass


class BaseEmailProvider:
    async def send(self, to: str, subject: str, html_body: str) -> bool:
        raise NotImplementedError


class ConsoleEmailProvider(BaseEmailProvider):
    async def send(self, to: str, subject: str, html_body: str) -> bool:
        logger.info(f"[Email-Console] To: {to} | Subject: {subject}\n{html_body}")
        return True


def get_email_provider() -> BaseEmailProvider:
    provider_key = (EMAIL_PROVIDER or "console").strip().lower()

    if provider_key == "console":
        return ConsoleEmailProvider()

    raise EmailError(
        f"Email provider '{provider_key}' is not implemented yet. "
        f"Add a provider class in email_service.py and register it."
    )


class EmailService:

    def __init__(self):
        self.provider = get_email_provider()

    async def send_email_verification(self, to: str, user_id: int, token: str) -> bool:
        link = f"{APP_BASE_URL}/verify-email?uid={user_id}&token={token}"
        html = f"""
        <div dir="rtl" style="font-family:Tahoma">
            <p>برای تایید ایمیل خود روی لینک زیر کلیک کنید:</p>
            <p><a href="{link}">{link}</a></p>
            <p>این لینک تا ۲۴ ساعت معتبر است.</p>
        </div>
        """
        return await self.provider.send(to, "تایید ایمیل - CuraLink AI", html)

    async def send_password_reset(self, to: str, user_id: int, token: str) -> bool:
        link = f"{APP_BASE_URL}/reset-password?uid={user_id}&token={token}"
        html = f"""
        <div dir="rtl" style="font-family:Tahoma">
            <p>برای تنظیم رمز عبور جدید روی لینک زیر کلیک کنید:</p>
            <p><a href="{link}">{link}</a></p>
            <p>این لینک تا ۳۰ دقیقه معتبر است. اگر این درخواست را شما نداده‌اید، این ایمیل را نادیده بگیرید.</p>
        </div>
        """
        return await self.provider.send(to, "بازیابی رمز عبور - CuraLink AI", html)

    async def send_doctor_approval_notice(self, to: str, approved: bool) -> bool:
        if approved:
            html = "<div dir='rtl' style='font-family:Tahoma'><p>حساب پزشکی شما تایید شد و اکنون می‌توانید وارد شوید.</p></div>"
            subject = "حساب شما تایید شد - CuraLink AI"
        else:
            html = "<div dir='rtl' style='font-family:Tahoma'><p>متاسفانه درخواست حساب پزشکی شما تایید نشد.</p></div>"
            subject = "وضعیت درخواست حساب پزشکی - CuraLink AI"
        return await self.provider.send(to, subject, html)