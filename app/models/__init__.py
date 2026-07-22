"""
app/models/__init__.py

SQLAlchemy ORM models.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class LocalUser(Base):
    __tablename__ = "local_users"

    id = Column(Integer, primary_key=True, index=True)

    wp_user_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nicename = Column(String, nullable=True)
    display_name = Column(String, nullable=True)

    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    national_id = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    analyses = relationship("AnalysisRecord", back_populates="user", order_by="AnalysisRecord.created_at.desc()")
    test_results = relationship("TestResult", back_populates="user", order_by="TestResult.test_date.desc()")
    family_members = relationship("FamilyMember", back_populates="user", order_by="FamilyMember.created_at")
    diet_plans = relationship("DietPlanRecord", back_populates="user", order_by="DietPlanRecord.created_at.desc()")
    visit_preps = relationship("VisitPrepRecord", back_populates="user", order_by="VisitPrepRecord.created_at.desc()")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    relation = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("LocalUser", back_populates="family_members")
    analyses = relationship("AnalysisRecord", back_populates="family_member")
    test_results = relationship("TestResult", back_populates="family_member")
    diet_plans = relationship("DietPlanRecord", back_populates="family_member")
    visit_preps = relationship("VisitPrepRecord", back_populates="family_member")


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    exam_type = Column(String, nullable=True)
    filename = Column(String, nullable=True)

    ocr_text = Column(Text, nullable=True)
    analysis_text = Column(Text, nullable=True)
    analysis_html = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("LocalUser", back_populates="analyses")
    family_member = relationship("FamilyMember", back_populates="analyses")
    test_results = relationship("TestResult", back_populates="analysis", order_by="TestResult.test_name")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_records.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    test_name = Column(String, nullable=False, index=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    status = Column(String, nullable=True)  # normal / high / low
    recommended_followup_days = Column(Integer, nullable=True)
    organ_category = Column(String, nullable=True)
    followup_reminder_sent = Column(Boolean, default=False, nullable=False)

    test_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("LocalUser", back_populates="test_results")
    family_member = relationship("FamilyMember", back_populates="test_results")
    analysis = relationship("AnalysisRecord", back_populates="test_results")


class DietPlanRecord(Base):
    __tablename__ = "diet_plan_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    context = Column(Text, nullable=True)
    plan_text = Column(Text, nullable=True)
    plan_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("LocalUser", back_populates="diet_plans")
    family_member = relationship("FamilyMember", back_populates="diet_plans")


class VisitPrepRecord(Base):
    __tablename__ = "visit_prep_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True, index=True)

    visit_reason = Column(Text, nullable=True)
    summary_text = Column(Text, nullable=True)
    summary_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("LocalUser", back_populates="visit_preps")
    family_member = relationship("FamilyMember", back_populates="visit_preps")