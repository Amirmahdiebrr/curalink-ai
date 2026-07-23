"""
app/services/zarinpal_service.py

Low-level wrapper around the Zarinpal REST API (v4): request a
payment (get a redirect URL) and verify a payment after the user
returns from the gateway. Contains no business logic about what the
payment is *for* — see payment_service.py for that.
"""

import httpx

from app.config import ZARINPAL_MERCHANT_ID, ZARINPAL_SANDBOX


if ZARINPAL_SANDBOX:
    REQUEST_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
    VERIFY_URL = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
    STARTPAY_URL = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"
else:
    REQUEST_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
    VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
    STARTPAY_URL = "https://www.zarinpal.com/pg/StartPay/{authority}"


class ZarinpalError(Exception):
    pass


async def request_payment(
    amount_toman: int,
    description: str,
    callback_url: str,
    mobile: str | None = None,
    email: str | None = None,
) -> dict:
    """
    از زرین‌پال یک "authority" برای این پرداخت می‌گیرد و لینک کامل
    درگاه را برمی‌گرداند تا کاربر به آن ریدایرکت شود.

    Returns: {"authority": str, "payment_url": str}
    Raises: ZarinpalError روی هر خطا
    """

    payload = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": amount_toman,
        "currency": "IRT",  # تومان
        "description": description,
        "callback_url": callback_url,
    }

    if mobile:
        payload["metadata"] = {"mobile": mobile}
    if email:
        payload.setdefault("metadata", {})["email"] = email

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(REQUEST_URL, json=payload)
    except httpx.RequestError as e:
        raise ZarinpalError(f"اتصال به درگاه پرداخت برقرار نشد: {e}")

    if response.status_code != 200:
        raise ZarinpalError(f"خطای درگاه پرداخت: {response.status_code} - {response.text[:300]}")

    data = response.json()
    result = data.get("data") or {}
    errors = data.get("errors") or []

    if errors or result.get("code") != 100:
        raise ZarinpalError(f"درگاه پرداخت درخواست را رد کرد: {errors or result}")

    authority = result["authority"]

    return {
        "authority": authority,
        "payment_url": STARTPAY_URL.format(authority=authority),
    }


async def verify_payment(amount_toman: int, authority: str) -> dict:
    """
    بعد از برگشت کاربر از درگاه، پرداخت را نزد زرین‌پال verify می‌کند.

    Returns: {"success": bool, "ref_id": str | None, "code": int}
    """

    payload = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": amount_toman,
        "currency": "IRT",
        "authority": authority,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(VERIFY_URL, json=payload)
    except httpx.RequestError as e:
        raise ZarinpalError(f"اتصال به درگاه پرداخت برای تایید برقرار نشد: {e}")

    if response.status_code != 200:
        raise ZarinpalError(f"خطای درگاه پرداخت هنگام تایید: {response.status_code} - {response.text[:300]}")

    data = response.json()
    result = data.get("data") or {}
    code = result.get("code")

    # code 100 = پرداخت موفق و تازه‌تایید‌شده
    # code 101 = این پرداخت قبلاً verify شده (idempotent؛ همچنان موفق حساب می‌شود)
    success = code in (100, 101)

    return {
        "success": success,
        "ref_id": result.get("ref_id"),
        "code": code,
    }