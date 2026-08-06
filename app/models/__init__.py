"""
app/models/__init__.py

SQLAlchemy ORM models.
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


# ==========================
# نقش‌های کاربری
# ==========================

ROLE_PATIENT = "patient"
ROLE_DOCTOR = "doctor"
ROLE_ORG_ADMIN = "org_admin"
ROLE_PLATFORM_ADMIN = "platform_admin"

VALID_ROLES = [ROLE_PATIENT, ROLE_DOCTOR, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN]

VERIFICATION_PENDING = "pending_review"
VERIFICATION_APPROVED = "approved"
VERIFICATION_REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    role = Column(String, nullable=False, default=ROLE_PATIENT, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    phone = Column(String, unique=True, index=True, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    display_name = Column(String, nullable=False)

    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    address = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)

    # ===== استان/شهر محل اقامت و آزمایشگاه/مرکز معرف =====
    province = Column(String, nullable=True)
    city = Column(String, nullable=True)
    referred_by_org_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # ===== پروفایل سلامت اولیه =====
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    blood_type = Column(String, nullable=True)
    chronic_diseases = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    surgeries_history = Column(Text, nullable=True)
    smoking_status = Column(String, nullable=True)
    activity_level = Column(String, nullable=True)

    # ===== مخاطب اضطراری و مراکز درمانی ترجیحی =====
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    preferred_hospital = Column(String, nullable=True)
    preferred_lab = Column(String, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    verification_status = Column(String, nullable=True)
    verification_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    analyses = relationship(
        "AnalysisRecord",
        back_populates="user",
        order_by="AnalysisRecord.created_at.desc()",
        foreign_keys="AnalysisRecord.user_id",
    )
    test_results = relationship("TestResult", back_populates="user", order_by="TestResult.test_date.desc()")
    family_members = relationship("FamilyMember", back_populates="user", order_by="FamilyMember.created_at")
    diet_plans = relationship("DietPlanRecord", back_populates="user", order_by="DietPlanRecord.created_at.desc()")
    visit_preps = relationship("VisitPrepRecord", back_populates="user", order_by="VisitPrepRecord.created_at.desc()")
    workout_plans = relationship("WorkoutPlanRecord", back_populates="user", order_by="WorkoutPlanRecord.created_at.desc()")

    doctor_profile = relationship(
        "DoctorProfile",
        back_populates="user",
        uselist=False,
        foreign_keys="DoctorProfile.user_id",
    )
    organization_profile = relationship("OrganizationProfile", back_populates="user", uselist=False)

    # آزمایشگاه/کلینیک/بیمارستانی که این کاربر را معرفی کرده (در صورت وجود).
    # از طریق backref، روی خودِ آن آزمایشگاه، referred_users لیست تمام
    # کاربرانی که با معرفی او ثبت‌نام کرده‌اند را برمی‌گرداند.
    referred_by_org = relationship(
        "User",
        remote_side=[id],
        foreign_keys=[referred_by_org_id],
        backref="referred_users",
    )


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    specialty = Column(String, nullable=True)
    medical_council_no = Column(String, nullable=True)
    license_document_path = Column(String, nullable=True)
    clinic_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="doctor_profile", foreign_keys=[user_id])


class OrganizationProfile(Base):
    __tablename__ = "organization_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    org_name = Column(String, nullable=False)
    org_type = Column(String, nullable=True)
    license_document_path = Column(String, nullable=True)
    api_key_hash = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="organization_profile")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    relation = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)

    # ===== پروفایل سلامت اولیه =====
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    blood_type = Column(String, nullable=True)
    chronic_diseases = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    surgeries_history = Column(Text, nullable=True)
    smoking_status = Column(String, nullable=True)
    activity_level = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="family_members")
    analyses = relationship("AnalysisRecord", back_populates="family_member")
    test_results = relationship("TestResult", back_populates="family_member")
    diet_plans = relationship("DietPlanRecord", back_populates="family_member")
    visit_preps = relationship("VisitPrepRecord", back_populates="family_member")
    workout_plans = relationship("WorkoutPlanRecord", back_populates="family_member")


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    exam_type = Column(String, nullable=True)
    filename = Column(String, nullable=True)

    ocr_text = Column(Text, nullable=True)
    analysis_text = Column(Text, nullable=True)
    analysis_html = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)

    reviewing_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    doctor_opinion_text = Column(Text, nullable=True)
    doctor_opinion_status = Column(String, nullable=True)
    doctor_opinion_at = Column(DateTime, nullable=True)

    review_status = Column(String, nullable=True)
    review_payment_status = Column(String, nullable=True)
    review_price_paid = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="analyses", foreign_keys=[user_id])
    family_member = relationship("FamilyMember", back_populates="analyses")
    test_results = relationship("TestResult", back_populates="analysis", order_by="TestResult.test_name")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_records.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    test_name = Column(String, nullable=False, index=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    status = Column(String, nullable=True)
    recommended_followup_days = Column(Integer, nullable=True)
    organ_category = Column(String, nullable=True)
    followup_reminder_sent = Column(Boolean, default=False, nullable=False)

    test_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="test_results")
    family_member = relationship("FamilyMember", back_populates="test_results")
    analysis = relationship("AnalysisRecord", back_populates="test_results")


class DietPlanRecord(Base):
    __tablename__ = "diet_plan_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    context = Column(Text, nullable=True)
    plan_text = Column(Text, nullable=True)
    plan_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="diet_plans")
    family_member = relationship("FamilyMember", back_populates="diet_plans")


class VisitPrepRecord(Base):
    __tablename__ = "visit_prep_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    visit_reason = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    summary_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="visit_preps")
    family_member = relationship("FamilyMember", back_populates="visit_preps")


class WorkoutPlanRecord(Base):
    __tablename__ = "workout_plan_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    goal = Column(String, nullable=True)
    fitness_level = Column(String, nullable=True)
    days_per_week = Column(Integer, nullable=True)
    equipment = Column(String, nullable=True)
    injuries = Column(Text, nullable=True)

    plan_text = Column(Text, nullable=True)
    plan_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="workout_plans")
    family_member = relationship("FamilyMember", back_populates="workout_plans")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    purpose = Column(String, nullable=False, index=True)
    code_hash = Column(String, nullable=False)

    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================
# Billing / Plans / Subscriptions
# ==========================

BILLING_PERIOD_WEEKLY = "weekly"
BILLING_PERIOD_MONTHLY = "monthly"

SUBSCRIPTION_ACTIVE = "active"
SUBSCRIPTION_EXPIRED = "expired"
SUBSCRIPTION_CANCELLED = "cancelled"

PAYMENT_PENDING = "pending"
PAYMENT_PAID = "paid"
PAYMENT_FAILED = "failed"

PURPOSE_EXAM_ANALYSIS = "exam_analysis"
PURPOSE_DIET_PLAN = "diet_plan"
PURPOSE_VISIT_PREP = "visit_prep"
PURPOSE_WORKOUT_PLAN = "workout_plan"
PURPOSE_DOCTOR_REVIEW = "doctor_review"
PURPOSE_SUBSCRIPTION = "subscription"

DOCTOR_REVIEW_NOT_REQUESTED = "not_requested"
DOCTOR_REVIEW_AWAITING_DOCTOR = "awaiting_doctor"
DOCTOR_REVIEW_REVIEWED = "reviewed"

DOCTOR_PAYOUT_PENDING = "pending"
DOCTOR_PAYOUT_PAID = "paid"


class ServicePricing(Base):
    __tablename__ = "service_pricing"

    id = Column(Integer, primary_key=True, index=True)
    service_key = Column(String, unique=True, nullable=False, index=True)
    price = Column(Integer, nullable=False)

    doctor_share = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    name_fa = Column(String, nullable=False)

    price = Column(Integer, nullable=False)
    billing_period_days = Column(Integer, nullable=False)

    usage_limit = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)

    status = Column(String, nullable=False, default=SUBSCRIPTION_ACTIVE, index=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    usage_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    purpose = Column(String, nullable=False, index=True)
    reference_id = Column(Integer, nullable=True)

    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default=PAYMENT_PENDING, index=True)

    zarinpal_authority = Column(String, nullable=True, index=True)
    zarinpal_ref_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="payments")


class DoctorPayout(Base):
    __tablename__ = "doctor_payouts"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_records.id"), nullable=False, index=True)

    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default=DOCTOR_PAYOUT_PENDING, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    doctor = relationship("User", foreign_keys=[doctor_id])


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    member_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("User", foreign_keys=[organization_user_id])
    member = relationship("User", foreign_keys=[member_user_id])


class JobRecord(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, nullable=False, index=True)

    exam_type = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(String, nullable=False, default="pending")
    stage = Column(String, nullable=False, default="pending")

    result_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PendingActionRecord(Base):
    __tablename__ = "pending_actions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), unique=True, nullable=False, index=True)

    data_json = Column(Text, nullable=False)
    result_type = Column(String, nullable=True)
    result_id = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)

    is_approved = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")