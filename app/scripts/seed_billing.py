"""
app/scripts/seed_billing.py
"""

from app.database import SessionLocal, init_db
from app.models import ServicePricing, Plan
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


SERVICE_PRICES = [
    {"service_key": "blood", "price": 70_000, "doctor_share": None},
    {"service_key": "urine", "price": 70_000, "doctor_share": None},
    {"service_key": "biochemistry", "price": 70_000, "doctor_share": None},
    {"service_key": "sonography", "price": 100_000, "doctor_share": None},
    {"service_key": "radiology", "price": 100_000, "doctor_share": None},
    {"service_key": "mri", "price": 130_000, "doctor_share": None},
    {"service_key": "ct_scan", "price": 130_000, "doctor_share": None},
    {"service_key": "mammography", "price": 130_000, "doctor_share": None},
    {"service_key": "hse", "price": 190_000, "doctor_share": None},
    {"service_key": "other", "price": 80_000, "doctor_share": None},

    {"service_key": "diet_plan", "price": 200_000, "doctor_share": None},
    {"service_key": "visit_prep", "price": 50_000, "doctor_share": None},
    {"service_key": "workout_plan", "price": 180_000, "doctor_share": None},

    {"service_key": "doctor_review", "price": 80_000, "doctor_share": 60_000},
]


PLANS = [
    {
        "code": "patient_weekly",
        "role": "patient",
        "name_fa": "اشتراک هفتگی بیمار",
        "price": 250_000,
        "billing_period_days": 7,
        "usage_limit": None,
    },
    {
        "code": "patient_monthly",
        "role": "patient",
        "name_fa": "اشتراک ماهانه بیمار",
        "price": 500_000,
        "billing_period_days": 30,
        "usage_limit": None,
    },
    {
        "code": "doctor_monthly",
        "role": "doctor",
        "name_fa": "اشتراک ماهانه پزشک",
        "price": 700_000,
        "billing_period_days": 30,
        "usage_limit": None,
    },
    {
        "code": "org_small_monthly",
        "role": "org_admin",
        "name_fa": "پلن سازمانی کوچک (مطب/کلینیک)",
        "price": 2_000_000,
        "billing_period_days": 30,
        "usage_limit": 50,
    },
    {
        "code": "org_lab_monthly",
        "role": "org_admin",
        "name_fa": "پلن سازمانی آزمایشگاه",
        "price": 7_500_000,
        "billing_period_days": 30,
        "usage_limit": 250,
    },
    {
        "code": "org_hospital_monthly",
        "role": "org_admin",
        "name_fa": "پلن سازمانی بیمارستان/بزرگ",
        "price": 20_000_000,
        "billing_period_days": 30,
        "usage_limit": 1000,
    },
]


DIET_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS = 4
WORKOUT_PLAN_WEEKLY_CAP_FOR_SUBSCRIBERS = 4


def upsert_service_pricing(db):
    for item in SERVICE_PRICES:
        existing = (
            db.query(ServicePricing)
            .filter(ServicePricing.service_key == item["service_key"])
            .first()
        )

        if existing:
            existing.price = item["price"]
            existing.doctor_share = item["doctor_share"]
            logger.info(f"[Seed] Updated pricing: {item['service_key']} -> {item['price']}")
        else:
            db.add(ServicePricing(
                service_key=item["service_key"],
                price=item["price"],
                doctor_share=item["doctor_share"],
            ))
            logger.info(f"[Seed] Created pricing: {item['service_key']} -> {item['price']}")

    db.commit()


def upsert_plans(db):
    for item in PLANS:
        existing = db.query(Plan).filter(Plan.code == item["code"]).first()

        if existing:
            existing.name_fa = item["name_fa"]
            existing.price = item["price"]
            existing.billing_period_days = item["billing_period_days"]
            existing.usage_limit = item["usage_limit"]
            existing.role = item["role"]
            logger.info(f"[Seed] Updated plan: {item['code']} -> {item['price']} تومان")
        else:
            db.add(Plan(
                code=item["code"],
                role=item["role"],
                name_fa=item["name_fa"],
                price=item["price"],
                billing_period_days=item["billing_period_days"],
                usage_limit=item["usage_limit"],
                is_active=True,
            ))
            logger.info(f"[Seed] Created plan: {item['code']} -> {item['price']} تومان")

    db.commit()


def main():
    init_db()

    db = SessionLocal()
    try:
        upsert_service_pricing(db)
        upsert_plans(db)
        logger.info("[Seed] Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()