"""
app/services/email_service.py

Provider-agnostic email sending layer. 'console' فقط لاگ می‌کند
(برای توسعه)؛ 'smtp' ایمیل واقعی از طریق SMTP ارسال می‌کند.
"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import (
    EMAIL_PROVIDER, APP_BASE_URL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS,
)
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


class SMTPEmailProvider(BaseEmailProvider):
    async def send(self, to: str, subject: str, html_body: str) -> bool:
        if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
            logger.error("[Email-SMTP] SMTP_HOST/SMTP_USER/SMTP_PASSWORD تنظیم نشده‌اند.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [to], msg.as_string())
            logger.info(f"[Email-SMTP] Sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"[Email-SMTP] Failed to send to {to}: {e}")
            return False


def get_email_provider() -> BaseEmailProvider:
    provider_key = (EMAIL_PROVIDER or "console").strip().lower()

    if provider_key == "console":
        return ConsoleEmailProvider()

    if provider_key == "smtp":
        return SMTPEmailProvider()

    raise EmailError(
        f"Email provider '{provider_key}' is not implemented yet."
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

    async def send_account_deleted_notice(self, to: str, by_admin: bool) -> bool:
        if by_admin:
            html = "<div dir='rtl' style='font-family:Tahoma'><p>حساب کاربری شما توسط تیم پشتیبانی حذف شد.</p></div>"
        else:
            html = "<div dir='rtl' style='font-family:Tahoma'><p>حساب کاربری شما با موفقیت حذف شد.</p></div>"
        return await self.provider.send(to, "حذف حساب کاربری - CuraLink AI", html)