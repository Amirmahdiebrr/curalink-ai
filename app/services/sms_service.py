"""
app/services/sms_service.py

Provider-agnostic SMS sending layer. Right now only a "console"
provider exists (logs the message instead of sending it), so the
rest of the app (reminder scheduler, etc.) can be built against a
stable interface before a real SMS panel is purchased.

To add a real provider later:
1. Create a class inheriting from BaseSMSProvider with a `send` method.
2. Register it in `get_sms_provider()` below.
3. Set SMS_PROVIDER in .env to the new provider's key.
"""

from __future__ import annotations

from app.config import SMS_PROVIDER
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SMSError(Exception):
    pass


class BaseSMSProvider:
    async def send(self, to: str, message: str) -> bool:
        raise NotImplementedError


class ConsoleSMSProvider(BaseSMSProvider):
    """
    Default/fallback provider. Does not send a real SMS - just logs it.
    Useful for local development and until a real panel is purchased.
    """

    async def send(self, to: str, message: str) -> bool:
        logger.info(f"[SMS-Console] To: {to} | Message: {message}")
        return True


# ==========================
# Future real providers go here, e.g.:
#
# class KavenegarProvider(BaseSMSProvider):
#     async def send(self, to: str, message: str) -> bool:
#         ...
#
# class MeliPayamakProvider(BaseSMSProvider):
#     async def send(self, to: str, message: str) -> bool:
#         ...
# ==========================


def get_sms_provider() -> BaseSMSProvider:
    provider_key = (SMS_PROVIDER or "console").strip().lower()

    if provider_key == "console":
        return ConsoleSMSProvider()

    raise SMSError(
        f"SMS provider '{provider_key}' is not implemented yet. "
        f"Add a provider class in sms_service.py and register it."
    )


class SMSService:

    def __init__(self):
        self.provider = get_sms_provider()

    async def send_reminder(self, phone: str, message: str) -> bool:
        if not phone:
            logger.info("[SMSService] Skipped: no phone number provided.")
            return False

        try:
            return await self.provider.send(phone, message)
        except SMSError as e:
            logger.error(f"[SMSService] Provider error: {e}")
            return False
        except Exception as e:
            logger.error(f"[SMSService] Unexpected error sending SMS: {e}")
            return False