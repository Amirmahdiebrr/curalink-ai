"""
app/services/payment_service.py

Bridges billing_service (what things cost, subscription state) and
zarinpal_service (the actual gateway calls) with the Payment table.
Handles creating a pending payment + redirect URL, and finalizing a
payment after the user returns from the gateway.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Payment, Plan, User,
    PAYMENT_PENDING, PAYMENT_PAID, PAYMENT_FAILED,
    PURPOSE_SUBSCRIPTION,
)
from app.services import zarinpal_service
from app.services.zarinpal_service import ZarinpalError
from app.services.billing_service import create_subscription, get_plan_by_code
from app.config import APP_BASE_URL


class PaymentError(Exception):
    pass


async def start_payment(
    db: Session,
    user: User,
    purpose: str,
    amount: int,
    description: str,
    reference_id: int | None = None,
) -> dict:
    """
    یک رکورد Payment در وضعیت pending می‌سازد و از زرین‌پال لینک
    پرداخت می‌گیرد. reference_id بسته به purpose معنا دارد (مثلاً
    برای PURPOSE_SUBSCRIPTION، شناسه‌ی Plan است).

    Returns: {"payment_id": int, "payment_url": str}
    """

    payment = Payment(
        user_id=user.id,
        purpose=purpose,
        reference_id=reference_id,
        amount=amount,
        status=PAYMENT_PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    callback_url = f"{APP_BASE_URL}/payment/callback?payment_id={payment.id}"

    try:
        result = await zarinpal_service.request_payment(
            amount_toman=amount,
            description=description,
            callback_url=callback_url,
            mobile=user.phone,
            email=user.email,
        )
    except ZarinpalError as e:
        payment.status = PAYMENT_FAILED
        db.commit()
        raise PaymentError(str(e))

    payment.zarinpal_authority = result["authority"]
    db.commit()

    return {"payment_id": payment.id, "payment_url": result["payment_url"]}


async def start_subscription_purchase(db: Session, user: User, plan_code: str) -> dict:
    """
    خرید یک پلن اشتراکی (بیمار/پزشک/سازمان) را آغاز می‌کند.
    """
    plan = get_plan_by_code(db, plan_code)

    if not plan:
        raise PaymentError("پلن انتخاب‌شده معتبر نیست.")

    if plan.role != user.role:
        raise PaymentError("این پلن برای نقش حساب کاربری شما نیست.")

    return await start_payment(
        db,
        user=user,
        purpose=PURPOSE_SUBSCRIPTION,
        amount=plan.price,
        description=f"خرید {plan.name_fa}",
        reference_id=plan.id,
    )


async def finalize_payment(db: Session, payment_id: int, authority: str) -> Payment:
    """
    بعد از برگشت کاربر از درگاه، پرداخت را verify می‌کند و در صورت
    موفقیت، اکشن مناسب (مثلاً فعال‌سازی اشتراک) را انجام می‌دهد.
    این تابع idempotent است: اگر پرداخت قبلاً paid شده باشد، دوباره
    اکشن تکراری انجام نمی‌دهد.
    """

    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise PaymentError("پرداخت مورد نظر پیدا نشد.")

    if payment.zarinpal_authority != authority:
        raise PaymentError("Authority ارسال‌شده با پرداخت مطابقت ندارد.")

    if payment.status == PAYMENT_PAID:
        # قبلاً پردازش شده (مثلاً کاربر صفحه را رفرش کرده)؛ کاری نکن.
        return payment

    try:
        verify_result = await zarinpal_service.verify_payment(
            amount_toman=payment.amount,
            authority=authority,
        )
    except ZarinpalError as e:
        payment.status = PAYMENT_FAILED
        db.commit()
        raise PaymentError(str(e))

    if not verify_result["success"]:
        payment.status = PAYMENT_FAILED
        db.commit()
        raise PaymentError("پرداخت توسط درگاه تایید نشد.")

    payment.status = PAYMENT_PAID
    payment.zarinpal_ref_id = verify_result["ref_id"]
    payment.paid_at = datetime.utcnow()
    db.commit()

    _apply_payment_effect(db, payment)

    return payment


def _apply_payment_effect(db: Session, payment: Payment) -> None:
    """
    بر اساس purpose پرداخت، اکشن نهایی را انجام می‌دهد. فعلاً فقط
    PURPOSE_SUBSCRIPTION پیاده‌سازی شده؛ purpose های دیگر (تحلیل
    آزمایش/برنامه‌غذایی/ویزیت‌پرپ/بررسی پزشک) در گام بعدی که این
    سرویس را به روترهای مربوطه وصل می‌کنیم اضافه می‌شوند.
    """

    if payment.purpose == PURPOSE_SUBSCRIPTION:
        plan = db.query(Plan).filter(Plan.id == payment.reference_id).first()
        if plan:
            create_subscription(db, payment.user_id, plan)
            print(f"[Payment] Subscription activated: user_id={payment.user_id}, plan={plan.code}", flush=True)
        else:
            print(f"[Payment] WARNING: plan not found for payment_id={payment.id}", flush=True)

    # سایر purpose ها (exam_analysis, diet_plan, visit_prep, doctor_review)
    # بعداً اینجا اضافه می‌شوند.