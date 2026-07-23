"""
app/services/billing_service.py

Core billing logic: service pricing lookup, subscription status
checks, weekly usage caps, and organization quota tracking. This
module contains NO payment gateway code (see zarinpal_service.py,
built in the next step) — it only answers "is this user allowed to
use X right now for free, and if not, how much do they need to pay?"
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    ServicePricing,
    Plan,
    Subscription,
    DietPlanRecord,
    OrganizationMember,
    SUBSCRIPTION_ACTIVE,
)


# سقف تعداد برنامه‌ی غذایی رایگان در هفته برای مشترکین (هفتگی/ماهانه).
# کاربرانی که pay-per-use پرداخت می‌کنند مشمول این سقف نیستند.
DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS = 4

PATIENT_SUBSCRIPTION_CODES = ("patient_weekly", "patient_monthly")
DOCTOR_SUBSCRIPTION_CODES = ("doctor_monthly",)
ORG_SUBSCRIPTION_CODES = ("org_small_monthly", "org_lab_monthly", "org_hospital_monthly")


class BillingError(Exception):
    pass


# ==========================
# Pricing lookups
# ==========================

def get_service_price(db: Session, service_key: str) -> int:
    pricing = db.query(ServicePricing).filter(ServicePricing.service_key == service_key).first()

    if not pricing:
        raise BillingError(f"قیمتی برای سرویس '{service_key}' تعریف نشده است.")

    return pricing.price


def get_doctor_review_pricing(db: Session) -> dict:
    pricing = db.query(ServicePricing).filter(ServicePricing.service_key == "doctor_review").first()

    if not pricing:
        raise BillingError("قیمتی برای بررسی پزشک تعریف نشده است.")

    return {
        "price": pricing.price,
        "doctor_share": pricing.doctor_share or 0,
        "platform_share": pricing.price - (pricing.doctor_share or 0),
    }


def get_plan_by_code(db: Session, code: str) -> Plan | None:
    return db.query(Plan).filter(Plan.code == code, Plan.is_active.is_(True)).first()


# ==========================
# Subscription status
# ==========================

def _expire_stale_subscriptions(db: Session, user_id: int):
    """
    اشتراک‌های منقضی‌شده (expires_at گذشته) که هنوز status=active
    مانده‌اند را به‌روزرسانی می‌کند. قبل از هر چک دسترسی صدا زده
    می‌شود تا هیچ‌وقت یک اشتراک تمام‌شده به‌اشتباه فعال به‌حساب نیاید.
    """
    now = datetime.utcnow()

    stale = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == SUBSCRIPTION_ACTIVE,
            Subscription.expires_at < now,
        )
        .all()
    )

    for sub in stale:
        sub.status = "expired"

    if stale:
        db.commit()


def get_active_subscription(db: Session, user_id: int, plan_codes: tuple[str, ...] | None = None) -> Subscription | None:
    _expire_stale_subscriptions(db, user_id)

    query = (
        db.query(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == SUBSCRIPTION_ACTIVE,
        )
    )

    if plan_codes:
        query = query.filter(Plan.code.in_(plan_codes))

    return query.order_by(Subscription.expires_at.desc()).first()


def patient_has_active_subscription(db: Session, user_id: int) -> Subscription | None:
    return get_active_subscription(db, user_id, PATIENT_SUBSCRIPTION_CODES)


def doctor_has_active_subscription(db: Session, user_id: int) -> Subscription | None:
    return get_active_subscription(db, user_id, DOCTOR_SUBSCRIPTION_CODES)


def org_has_active_subscription(db: Session, org_user_id: int) -> Subscription | None:
    return get_active_subscription(db, org_user_id, ORG_SUBSCRIPTION_CODES)


def create_subscription(db: Session, user_id: int, plan: Plan) -> Subscription:
    """
    یک اشتراک جدید فعال می‌سازد. اگر اشتراک فعالِ قبلیِ همان نقش
    وجود داشته باشد، آن را cancel می‌کند (یک کاربر در آن واحد فقط یک
    اشتراک فعال از یک دسته دارد).
    """
    now = datetime.utcnow()

    existing_active = get_active_subscription(db, user_id)
    if existing_active and existing_active.plan.role == plan.role:
        existing_active.status = "cancelled"

    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        status=SUBSCRIPTION_ACTIVE,
        started_at=now,
        expires_at=now + timedelta(days=plan.billing_period_days),
        usage_count=0,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


# ==========================
# Patient: exam analysis / visit-prep access
#
# این دو مورد برای بیمار مشترک همیشه نامحدود و رایگانند (بدون سقف
# هفتگی)؛ فقط برنامه‌ی غذایی سقف جدا دارد (پایین‌تر).
# ==========================

def patient_can_use_free(db: Session, user_id: int) -> bool:
    """
    آیا این بیمار یک اشتراک فعال (هفتگی/ماهانه) دارد که تحلیل آزمایش
    و آماده‌سازی ویزیت را برایش رایگان می‌کند؟
    """
    return patient_has_active_subscription(db, user_id) is not None


# ==========================
# Patient: diet plan access (has its own weekly cap for subscribers)
# ==========================

def _diet_plans_used_this_week(db: Session, user_id: int) -> int:
    week_ago = datetime.utcnow() - timedelta(days=7)

    return (
        db.query(DietPlanRecord)
        .filter(
            DietPlanRecord.user_id == user_id,
            DietPlanRecord.created_at >= week_ago,
        )
        .count()
    )


def check_diet_plan_access(db: Session, user_id: int) -> dict:
    """
    بررسی می‌کند این کاربر می‌تواند برنامه‌ی غذایی رایگان (از طریق
    اشتراک) بگیرد یا باید pay-per-use پرداخت کند.

    خروجی:
    {
        "free": bool,           # اگر True، رایگان از طریق اشتراک مجاز است
        "requires_payment": bool,
        "price": int | None,    # فقط اگر requires_payment باشد
        "reason": str,
    }
    """
    subscription = patient_has_active_subscription(db, user_id)

    if subscription:
        used = _diet_plans_used_this_week(db, user_id)

        if used < DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS:
            return {"free": True, "requires_payment": False, "price": None, "reason": "covered_by_subscription"}

        # سقف رایگان این هفته پر شده؛ کاربر می‌تواند با پرداخت جداگانه
        # (pay-per-use) باز هم برنامه بگیرد — سقفی برای pay-per-use
        # وجود ندارد (طبق تصمیم گرفته‌شده).
        price = get_service_price(db, "diet_plan")
        return {
            "free": False,
            "requires_payment": True,
            "price": price,
            "reason": f"سقف {DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS} برنامه‌ی رایگان در هفته پر شده است.",
        }

    price = get_service_price(db, "diet_plan")
    return {"free": False, "requires_payment": True, "price": price, "reason": "no_active_subscription"}


# ==========================
# Organization quota
# ==========================

def get_organization_for_member(db: Session, member_user_id: int) -> int | None:
    """
    اگر این کاربر پرسنل زیرمجموعه‌ی یک سازمان باشد، user_id سازمان
    (org_admin) را برمی‌گرداند؛ در غیر این صورت None.
    """
    link = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.member_user_id == member_user_id)
        .first()
    )
    return link.organization_user_id if link else None


def check_organization_quota(db: Session, org_user_id: int) -> dict:
    """
    وضعیت سهمیه‌ی ماهانه‌ی سازمان را برمی‌گرداند.
    خروجی:
    {
        "has_active_plan": bool,
        "limit": int | None,
        "used": int,
        "remaining": int | None,
    }
    """
    subscription = org_has_active_subscription(db, org_user_id)

    if not subscription:
        return {"has_active_plan": False, "limit": None, "used": 0, "remaining": None}

    limit = subscription.plan.usage_limit
    used = subscription.usage_count
    remaining = None if limit is None else max(limit - used, 0)

    return {
        "has_active_plan": True,
        "limit": limit,
        "used": used,
        "remaining": remaining,
    }


def increment_organization_usage(db: Session, org_user_id: int) -> None:
    subscription = org_has_active_subscription(db, org_user_id)

    if subscription:
        subscription.usage_count += 1
        db.commit()


# ==========================
# Doctor review access
# ==========================

def patient_review_is_free(db: Session, patient_user_id: int) -> bool:
    """
    اگر بیمار اشتراک فعال دارد، درخواست بررسی پزشک برایش رایگان است
    (هزینه‌ی پزشک را خود پلتفرم از جیب خودش می‌پردازد).
    """
    return patient_has_active_subscription(db, patient_user_id) is not None