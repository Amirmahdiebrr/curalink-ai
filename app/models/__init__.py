"""
app/models/__init__.py

SQLAlchemy ORM models.

این نسخه جایگزین کامل مدل قدیمی LocalUser (که وابسته به وردپرس بود) است.
حساب کاربری حالا مستقل است و از چند نقش پشتیبانی می‌کند:
patient / doctor / org_admin / platform_admin
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

    is_active = Column(Boolean, default=True, nullable=False)
    verification_status = Column(String, nullable=True)
    verification_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    analyses = relationship("AnalysisRecord", back_populates="user", order_by="AnalysisRecord.created_at.desc()")
    test_results = relationship("TestResult", back_populates="user", order_by="TestResult.test_date.desc()")
    family_members = relationship("FamilyMember", back_populates="user", order_by="FamilyMember.created_at")
    diet_plans = relationship("DietPlanRecord", back_populates="user", order_by="DietPlanRecord.created_at.desc()")
    visit_preps = relationship("VisitPrepRecord", back_populates="user", order_by="VisitPrepRecord.created_at.desc()")

    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    organization_profile = relationship("OrganizationProfile", back_populates="user", uselist=False)


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

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="family_members")
    analyses = relationship("AnalysisRecord", back_populates="family_member")
    test_results = relationship("TestResult", back_populates="family_member")
    diet_plans = relationship("DietPlanRecord", back_populates="family_member")
    visit_preps = relationship("VisitPrepRecord", back_populates="family_member")


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


class VerificationCode(Base):
    """
    کدهای یک‌بارمصرف برای تایید ایمیل، تایید موبایل (OTP)، و بازیابی رمز عبور.
    purpose: 'email_verify' | 'phone_otp' | 'password_reset'
    """
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    purpose = Column(String, nullable=False, index=True)
    code_hash = Column(String, nullable=False)

    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)