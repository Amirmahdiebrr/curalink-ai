"""
tests/conftest.py

فیکسچرهای مشترک pytest: یک دیتابیس SQLite جداگانه و موقت برای هر
اجرای تست (نه دیتابیس واقعی پروژه)، به‌علاوه یک session تمیز برای
هر تست تا تست‌ها روی هم اثر نگذارند.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("APP_BASE_URL", "http://localhost:8000")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models  # noqa: F401 — registers all models on Base.metadata


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def db_session():
    """
    یک دیتابیس SQLite کاملاً در-حافظه (in-memory) برای هر تست جداگانه
    می‌سازد؛ بعد از پایان تست، خودش از بین می‌رود و اثری روی دیتابیس
    واقعی پروژه نمی‌گذارد.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()