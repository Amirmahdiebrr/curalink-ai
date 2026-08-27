"""
app/services/payment_service.py
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Payment, Plan, User,
    PAYMENT_PENDING, PAYMENT_PAID, PAYMENT_FAILED,
    PURPOSE_SUBSCRIPTION, PURPOSE_EXAM_ANALYSIS, PURPOSE_DIET_PLAN,
    PURPOSE_VISIT_PREP, PURPOSE_WORKOUT_PLAN, PURPOSE_DOCTOR_REVIEW,
)
from app.services import zarinpal_service
from app.services import pending_action_store
from app.services.zarinpal_service import ZarinpalError
from app.services.billing_service import create_subscription, get_plan_by_code
from app.config import APP_BASE_URL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

GENERIC_GATEWAY_ERROR = "اتصال به درگاه پرداخت برقرار نشد. لطفاً چند لحظه دیگر دوباره تلاش کنید."
GENERIC_VERIFY_ERROR = "تایید پرداخت ناموفق بود. در صورت کسر وجه، مبلغ ظرف ۷۲ ساعت به حساب شما بازمی‌گردد."


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
        logger.error(f"[Payment] Gateway request failed for payment_id={payment.id}: {e}")
        raise PaymentError(GENERIC_GATEWAY_ERROR)

    payment.zarinpal_authority = result["authority"]
    db.commit()

    return {"payment_id": payment.id, "payment_url": result["payment_url"]}


async def start_subscription_purchase(db: Session, user: User, plan_code: str) -> dict:
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


async def start_service_payment(
    db: Session,
    user: User,
    purpose: str,
    amount: int,
    description: str,
    pending_data: dict,
) -> dict:
    result = await start_payment(db, user=user, purpose=purpose, amount=amount, description=description)
    pending_action_store.save(result["payment_id"], pending_data)
    return result


async def finalize_payment(db: Session, payment_id: int, authority: str) -> Payment:

    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise PaymentError("پرداخت مورد نظر پیدا نشد.")

    if payment.zarinpal_authority != authority:
        logger.error(f"[Payment] Authority mismatch for payment_id={payment_id}")
        raise PaymentError(GENERIC_VERIFY_ERROR)

    if payment.status == PAYMENT_PAID:
        return payment

    try:
        verify_result = await zarinpal_service.verify_payment(
            amount_toman=payment.amount,
            authority=authority,
        )
    except ZarinpalError as e:
        payment.status = PAYMENT_FAILED
        db.commit()
        logger.error(f"[Payment] Gateway verify failed for payment_id={payment.id}: {e}")
        raise PaymentError(GENERIC_VERIFY_ERROR)

    if not verify_result["success"]:
        payment.status = PAYMENT_FAILED
        db.commit()
        logger.error(f"[Payment] Gateway rejected verify for payment_id={payment.id}: code={verify_result.get('code')}")
        raise PaymentError(GENERIC_VERIFY_ERROR)

    payment.status = PAYMENT_PAID
    payment.zarinpal_ref_id = verify_result["ref_id"]
    payment.paid_at = datetime.utcnow()
    db.commit()

    await _apply_payment_effect(db, payment)

    return payment


async def _apply_payment_effect(db: Session, payment: Payment) -> None:

    if payment.purpose == PURPOSE_SUBSCRIPTION:
        plan = db.query(Plan).filter(Plan.id == payment.reference_id).first()
        if plan:
            create_subscription(db, payment.user_id, plan)
            logger.info(f"[Payment] Subscription activated: user_id={payment.user_id}, plan={plan.code}")
        else:
            logger.warning(f"[Payment] WARNING: plan not found for payment_id={payment.id}")
        return

    action = pending_action_store.get(payment.id)

    if not action:
        logger.warning(f"[Payment] WARNING: no pending action found for payment_id={payment.id}")
        return

    try:
        if payment.purpose == PURPOSE_EXAM_ANALYSIS:
            from app.routers.analyze import start_background_job
            job_id = await start_background_job(action["data"])
            pending_action_store.update(payment.id, result_type="job", result_id=job_id)
            logger.info(f"[Payment] Exam analysis job started: payment_id={payment.id}, job_id={job_id}")

        elif payment.purpose == PURPOSE_DIET_PLAN:
            from app.routers.diet import start_diet_background_job
            job_id = await start_diet_background_job(action["data"], payment.user_id)
            pending_action_store.update(payment.id, result_type="generic_job", result_id=job_id)
            logger.info(f"[Payment] Diet background job started: payment_id={payment.id}, job_id={job_id}")

        elif payment.purpose == PURPOSE_VISIT_PREP:
            from app.routers.visit_prep import start_visit_prep_background_job
            job_id = await start_visit_prep_background_job(action["data"], payment.user_id)
            pending_action_store.update(payment.id, result_type="generic_job", result_id=job_id)
            logger.info(f"[Payment] Visit-prep background job started: payment_id={payment.id}, job_id={job_id}")

        elif payment.purpose == PURPOSE_WORKOUT_PLAN:
            from app.routers.workout import start_workout_background_job
            job_id = await start_workout_background_job(action["data"], payment.user_id)
            pending_action_store.update(payment.id, result_type="generic_job", result_id=job_id)
            logger.info(f"[Payment] Workout background job started: payment_id={payment.id}, job_id={job_id}")

        elif payment.purpose == PURPOSE_DOCTOR_REVIEW:
            from app.services.doctor_review_service import mark_review_requested, DoctorReviewError
            data = action["data"]
            try:
                record = mark_review_requested(
                    db,
                    record_id=data["record_id"],
                    user_id=data["user_id"],
                    price_paid=data.get("price_paid"),
                )
                pending_action_store.update(payment.id, result_type="doctor_review", result_id=record.id)
                logger.info(f"[Payment] Doctor review marked as requested: payment_id={payment.id}, record_id={record.id}")
            except DoctorReviewError as e:
                pending_action_store.update(payment.id, error="ثبت درخواست بررسی پزشک با خطا مواجه شد.")
                logger.error(f"[Payment] Doctor review request failed after payment: {e}")

        else:
            logger.warning(f"[Payment] WARNING: unknown purpose '{payment.purpose}' for payment_id={payment.id}")

    except Exception as e:
        logger.error(f"[Payment] Failed to apply effect for payment_id={payment.id}: {e}")
        pending_action_store.update(payment.id, error="پردازش درخواست شما پس از پرداخت با خطا مواجه شد.")