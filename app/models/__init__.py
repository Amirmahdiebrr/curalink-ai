"""
app/models/__init__.py

SQLAlchemy ORM models.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey
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

    created_at = Column(DateTime, default=datetime.utcnow)

    analyses = relationship("AnalysisRecord", back_populates="user", order_by="AnalysisRecord.created_at.desc()")
    test_results = relationship("TestResult", back_populates="user", order_by="TestResult.test_date.desc()")


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)

    exam_type = Column(String, nullable=True)
    filename = Column(String, nullable=True)

    ocr_text = Column(Text, nullable=True)
    analysis_text = Column(Text, nullable=True)
    analysis_html = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("LocalUser", back_populates="analyses")
    test_results = relationship("TestResult", back_populates="analysis", order_by="TestResult.test_name")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("local_users.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_records.id"), nullable=False, index=True)

    test_name = Column(String, nullable=False, index=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    status = Column(String, nullable=True)  # normal / high / low

    test_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("LocalUser", back_populates="test_results")
    analysis = relationship("AnalysisRecord", back_populates="test_results")