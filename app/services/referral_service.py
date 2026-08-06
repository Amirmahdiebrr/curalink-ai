"""
app/services/referral_service.py

Referral tracking: at signup a patient can optionally select a
referring lab/clinic/hospital (an org_admin account). This service
aggregates who was referred by which organization, what they paid
for, and the total amount paid per month — so the platform can
calculate and pay the organization's referral bonus.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import User, Payment, PAYMENT_PAID, ROLE_ORG_ADMIN


def get_all_labs(db: Session):
    """
    آزمایشگاه‌ها/کلینیک‌ها/بیمارستان‌های ثبت‌شده که هنگام ثبت‌نام بیمار
    به‌عنوان «معرف» قابل انتخاب هستند.
    """
    return (
        db.query(User)
        .filter(User.role == ROLE_ORG_ADMIN, User.is_active.is_(True))
        .order_by(User.display_name)
        .all()
    )


def get_referred_users(db: Session, org_user_id: int):
    return (
        db.query(User)
        .filter(User.referred_by_org_id == org_user_id)
        .order_by(User.created_at.desc())
        .all()
    )


def get_referral_transactions(db: Session, org_user_id: int):
    """
    تمام تراکنش‌های موفق کاربرانی که با معرفی این آزمایشگاه ثبت‌نام
    کرده‌اند، جدیدترین در ابتدا.
    """
    referred_ids = [
        row[0]
        for row in db.query(User.id).filter(User.referred_by_org_id == org_user_id).all()
    ]

    if not referred_ids:
        return []

    return (
        db.query(Payment)
        .filter(Payment.user_id.in_(referred_ids), Payment.status == PAYMENT_PAID)
        .order_by(Payment.paid_at.desc())
        .all()
    )


def get_monthly_referral_totals(db: Session, org_user_id: int):
    """
    مجموع مبلغ تراکنش‌های موفق معرفی‌شدگان را به تفکیک ماه برمی‌گرداند
    (برای محاسبه‌ی بونوس دعوت)، جدیدترین ماه در ابتدا.
    """
    transactions = get_referral_transactions(db, org_user_id)

    buckets = defaultdict(lambda: {"total": 0, "count": 0})

    for payment in transactions:
        paid_at = payment.paid_at or payment.created_at
        key = (paid_at.year, paid_at.month)
        buckets[key]["total"] += payment.amount
        buckets[key]["count"] += 1

    result = []

    for (year, month), data in buckets.items():
        result.append({
            "year": year,
            "month": month,
            "label": f"{year}-{month:02d}",
            "total": data["total"],
            "count": data["count"],
        })

    result.sort(key=lambda item: (item["year"], item["month"]), reverse=True)

    return result


def get_referral_summary(db: Session, org_user_id: int) -> dict:
    referred_users = get_referred_users(db, org_user_id)
    transactions = get_referral_transactions(db, org_user_id)
    monthly_totals = get_monthly_referral_totals(db, org_user_id)

    total_paid = sum(p.amount for p in transactions)

    return {
        "referred_users": referred_users,
        "transactions": transactions,
        "monthly_totals": monthly_totals,
        "total_paid": total_paid,
        "total_referred_count": len(referred_users),
    }