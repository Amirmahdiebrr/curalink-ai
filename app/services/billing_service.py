"""
app/services/billing_service.py
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    ServicePricing,
    Plan,
    Subscription,
    DietPlanRecord,
    WorkoutPlanRecord,
    OrganizationMember,
    User,
    SUBSCRIPTION_ACTIVE,
    ROLE_PLATFORM_ADMIN,
)


DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS = 4
WORKOUT_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS = 4

PATIENT_SUBSCRIPTION_CODES = ("patient_weekly", "patient_monthly")
DOCTOR_SUBSCRIPTION_CODES = ("doctor_monthly",)
ORG_SUBSCRIPTION_CODES = ("org_small_monthly", "org_lab_monthly", "org_hospital_monthly")


class BillingError(Exception):
    pass


def _get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _is_platform_admin(db: Session, user_id: int) -> bool:
    user = _get_user(db, user_id)
    return bool(user and user.role == ROLE_PLATFORM_ADMIN)


def has_unlimited_access(db: Session, user_id: int) -> bool:
    """
    True اگر کاربر platform_admin باشد یا ادمین به‌صراحت دسترسی
    نامحدود و رایگان به همه‌ی سرویس‌ها را برایش فعال کرده باشد.
    """
    user = _get_user(db, user_id)
    if not user:
        return False
    return user.role == ROLE_PLATFORM_ADMIN or bool(user.unlimited_access)


def grant_unlimited_access(db: Session, target_user_id: int, granted_by_admin_id: int) -> User:
    user = _get_user(db, target_user_id)

    if not user:
        raise BillingError("کاربر مورد نظر پیدا نشد.")

    user.unlimited_access = True
    user.unlimited_access_granted_by = granted_by_admin_id
    user.unlimited_access_granted_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user


def revoke_unlimited_access(db: Session, target_user_id: int) -> User:
    user = _get_user(db, target_user_id)

    if not user:
        raise BillingError("کاربر مورد نظر پیدا نشد.")

    user.unlimited_access = False
    user.unlimited_access_granted_by = None
    user.unlimited_access_granted_at = None

    db.commit()
    db.refresh(user)

    return user


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


def _expire_stale_subscriptions(db: Session, user_id: int):
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


def patient_can_use_free(db: Session, user_id: int) -> bool:
    return patient_has_active_subscription(db, user_id) is not None


def check_exam_access(db: Session, user_id: int, exam_type: str) -> dict:

    if has_unlimited_access(db, user_id):
        return {
            "free": True, "requires_payment": False, "price": None,
            "reason": "unlimited_access_granted", "org_covered": False, "org_user_id": None,
        }

    if patient_has_active_subscription(db, user_id):
        return {
            "free": True, "requires_payment": False, "price": None,
            "reason": "covered_by_subscription", "org_covered": False, "org_user_id": None,
        }

    org_user_id = get_organization_for_member(db, user_id)

    if org_user_id:
        quota = check_organization_quota(db, org_user_id)

        if quota["has_active_plan"] and (quota["remaining"] is None or quota["remaining"] > 0):
            return {
                "free": True, "requires_payment": False, "price": None,
                "reason": "covered_by_organization", "org_covered": True, "org_user_id": org_user_id,
            }

    price = get_service_price(db, exam_type)

    return {
        "free": False, "requires_payment": True, "price": price,
        "reason": "no_active_subscription", "org_covered": False, "org_user_id": None,
    }


def check_visit_prep_access(db: Session, user_id: int) -> dict:

    if has_unlimited_access(db, user_id):
        return {"free": True, "requires_payment": False, "price": None, "reason": "unlimited_access_granted"}

    if patient_has_active_subscription(db, user_id):
        return {"free": True, "requires_payment": False, "price": None, "reason": "covered_by_subscription"}

    price = get_service_price(db, "visit_prep")
    return {"free": False, "requires_payment": True, "price": price, "reason": "no_active_subscription"}


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

    if has_unlimited_access(db, user_id):
        return {"free": True, "requires_payment": False, "price": None, "reason": "unlimited_access_granted"}

    subscription = patient_has_active_subscription(db, user_id)

    if subscription:
        used = _diet_plans_used_this_week(db, user_id)

        if used < DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS:
            return {"free": True, "requires_payment": False, "price": None, "reason": "covered_by_subscription"}

        price = get_service_price(db, "diet_plan")
        return {
            "free": False,
            "requires_payment": True,
            "price": price,
            "reason": f"سقف {DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS} برنامه‌ی رایگان در هفته پر شده است.",
        }

    price = get_service_price(db, "diet_plan")
    return {"free": False, "requires_payment": True, "price": price, "reason": "no_active_subscription"}


def _workout_plans_used_this_week(db: Session, user_id: int) -> int:
    week_ago = datetime.utcnow() - timedelta(days=7)

    return (
        db.query(WorkoutPlanRecord)
        .filter(
            WorkoutPlanRecord.user_id == user_id,
            WorkoutPlanRecord.created_at >= week_ago,
        )
        .count()
    )


def check_workout_plan_access(db: Session, user_id: int) -> dict:

    if has_unlimited_access(db, user_id):
        return {"free": True, "requires_payment": False, "price": None, "reason": "unlimited_access_granted"}

    subscription = patient_has_active_subscription(db, user_id)

    if subscription:
        used = _workout_plans_used_this_week(db, user_id)

        if used < WORKOUT_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS:
            return {"free": True, "requires_payment": False, "price": None, "reason": "covered_by_subscription"}

        price = get_service_price(db, "workout_plan")
        return {
            "free": False,
            "requires_payment": True,
            "price": price,
            "reason": f"سقف {WORKOUT_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS} برنامه‌ی رایگان در هفته پر شده است.",
        }

    price = get_service_price(db, "workout_plan")
    return {"free": False, "requires_payment": True, "price": price, "reason": "no_active_subscription"}


def get_organization_for_member(db: Session, member_user_id: int) -> int | None:
    link = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.member_user_id == member_user_id)
        .first()
    )
    return link.organization_user_id if link else None


def check_organization_quota(db: Session, org_user_id: int) -> dict:
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


def patient_review_is_free(db: Session, patient_user_id: int) -> bool:
    return has_unlimited_access(db, patient_user_id) or patient_has_active_subscription(db, patient_user_id) is not None