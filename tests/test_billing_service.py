"""
tests/test_billing_service.py

تست‌های حداقلی برای منطق قیمت‌گذاری و دسترسی رایگان/پولی.
"""

import pytest
from datetime import datetime, timedelta

from app.services.auth_service import register_patient
from app.services.billing_service import (
    has_unlimited_access,
    grant_unlimited_access,
    revoke_unlimited_access,
    get_service_price,
    check_exam_access,
    check_diet_plan_access,
    create_subscription,
    BillingError,
)
from app.models import ServicePricing, Plan


def _make_user(db_session, email="patient@example.com", phone="09120000001"):
    return register_patient(
        db_session, email=email, phone=phone, password="abcd1234", display_name="بیمار تست"
    )


def _seed_pricing(db_session, service_key="blood", price=70000):
    pricing = ServicePricing(service_key=service_key, price=price)
    db_session.add(pricing)
    db_session.commit()
    return pricing


def _seed_plan(db_session, code="patient_weekly", role="patient", price=250000, days=7):
    plan = Plan(
        code=code, role=role, name_fa="اشتراک تست",
        price=price, billing_period_days=days, usage_limit=None, is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_get_service_price_raises_for_unknown_service(db_session):
    with pytest.raises(BillingError):
        get_service_price(db_session, "unknown_service_key")


def test_get_service_price_returns_seeded_price(db_session):
    _seed_pricing(db_session, "blood", 70000)
    price = get_service_price(db_session, "blood")
    assert price == 70000


def test_check_exam_access_requires_payment_without_subscription(db_session):
    user = _make_user(db_session)
    _seed_pricing(db_session, "blood", 70000)

    access = check_exam_access(db_session, user.id, "blood")

    assert access["free"] is False
    assert access["price"] == 70000


def test_check_exam_access_free_with_unlimited_access(db_session):
    admin = _make_user(db_session, "admin@example.com", "09120000002")
    user = _make_user(db_session, "member@example.com", "09120000003")
    _seed_pricing(db_session, "blood", 70000)

    grant_unlimited_access(db_session, user.id, admin.id)

    access = check_exam_access(db_session, user.id, "blood")

    assert access["free"] is True
    assert access["reason"] == "unlimited_access_granted"


def test_revoke_unlimited_access_restores_payment_requirement(db_session):
    admin = _make_user(db_session, "admin2@example.com", "09120000004")
    user = _make_user(db_session, "member2@example.com", "09120000005")
    _seed_pricing(db_session, "blood", 70000)

    grant_unlimited_access(db_session, user.id, admin.id)
    assert has_unlimited_access(db_session, user.id) is True

    revoke_unlimited_access(db_session, user.id)
    assert has_unlimited_access(db_session, user.id) is False

    access = check_exam_access(db_session, user.id, "blood")
    assert access["free"] is False


def test_check_exam_access_free_with_active_subscription(db_session):
    user = _make_user(db_session, "subscriber@example.com", "09120000006")
    _seed_pricing(db_session, "blood", 70000)
    plan = _seed_plan(db_session)

    create_subscription(db_session, user.id, plan)

    access = check_exam_access(db_session, user.id, "blood")

    assert access["free"] is True
    assert access["reason"] == "covered_by_subscription"


def test_check_diet_plan_access_weekly_cap(db_session):
    from app.models import DietPlanRecord

    user = _make_user(db_session, "dietuser@example.com", "09120000007")
    _seed_pricing(db_session, "diet_plan", 200000)
    plan = _seed_plan(db_session, code="patient_weekly_diet")

    create_subscription(db_session, user.id, plan)

    # زیر سقف هفتگی (۴ برنامه) -> باید رایگان باشد
    for _ in range(3):
        db_session.add(DietPlanRecord(user_id=user.id, family_member_id=None, plan_text="x", plan_html="x"))
    db_session.commit()

    access_under_cap = check_diet_plan_access(db_session, user.id)
    assert access_under_cap["free"] is True

    # رسیدن به سقف -> باید پولی بشود
    db_session.add(DietPlanRecord(user_id=user.id, family_member_id=None, plan_text="x", plan_html="x"))
    db_session.commit()

    access_over_cap = check_diet_plan_access(db_session, user.id)
    assert access_over_cap["free"] is False
    assert access_over_cap["price"] == 200000