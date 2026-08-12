"""
app/database.py
"""

from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.logging_config import get_logger

logger = get_logger(__name__)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/lab_analyzer.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(conn, table: str, column: str, ddl_type: str):
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns(table)}

    if column not in existing_columns:
        logger.info(f"[DB Migration] Adding missing column '{column}' to {table}...")
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        conn.commit()
        logger.info(f"[DB Migration] Column '{column}' added successfully to {table}.")


def _drop_column_if_exists(conn, table: str, column: str):
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns(table)}

    if column in existing_columns:
        logger.info(f"[DB Migration] Dropping stray column '{column}' from {table}...")
        try:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
            conn.commit()
            logger.info(f"[DB Migration] Column '{column}' dropped successfully from {table}.")
        except Exception as e:
            logger.warning(f"[DB Migration] Failed to drop column '{column}' from {table} (older SQLite?): {e}")


HEALTH_PROFILE_COLUMNS = [
    ("height_cm", "INTEGER"),
    ("weight_kg", "FLOAT"),
    ("blood_type", "TEXT"),
    ("chronic_diseases", "TEXT"),
    ("allergies", "TEXT"),
    ("current_medications", "TEXT"),
    ("surgeries_history", "TEXT"),
    ("smoking_status", "TEXT"),
    ("activity_level", "TEXT"),
]

EMERGENCY_CONTACT_COLUMNS = [
    ("emergency_contact_name", "TEXT"),
    ("emergency_contact_phone", "TEXT"),
    ("preferred_hospital", "TEXT"),
    ("preferred_lab", "TEXT"),
]

REFERRAL_COLUMNS = [
    ("province", "TEXT"),
    ("city", "TEXT"),
    ("referred_by_org_id", "INTEGER"),
]

INSURANCE_COLUMNS = [
    ("insurance_type", "TEXT"),
    ("insurance_number", "TEXT"),
]


def _run_light_migrations():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "local_users" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "local_users", "phone", "TEXT")

    if "analysis_records" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "analysis_records", "symptoms", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "family_member_id", "INTEGER")
            _add_column_if_missing(conn, "analysis_records", "review_status", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "review_payment_status", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "review_price_paid", "INTEGER")

    if "test_results" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "test_results", "family_member_id", "INTEGER")
            _add_column_if_missing(conn, "test_results", "recommended_followup_days", "INTEGER")
            _add_column_if_missing(conn, "test_results", "organ_category", "TEXT")
            _add_column_if_missing(conn, "test_results", "followup_reminder_sent", "BOOLEAN DEFAULT 0")

    if "users" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "users", "avatar_path", "TEXT")
            for column, ddl_type in HEALTH_PROFILE_COLUMNS:
                _add_column_if_missing(conn, "users", column, ddl_type)
            for column, ddl_type in EMERGENCY_CONTACT_COLUMNS:
                _add_column_if_missing(conn, "users", column, ddl_type)
            for column, ddl_type in REFERRAL_COLUMNS:
                _add_column_if_missing(conn, "users", column, ddl_type)
            for column, ddl_type in INSURANCE_COLUMNS:
                _add_column_if_missing(conn, "users", column, ddl_type)

    if "family_members" in table_names:
        with engine.connect() as conn:
            for column, ddl_type in HEALTH_PROFILE_COLUMNS:
                _add_column_if_missing(conn, "family_members", column, ddl_type)

    if "prescriptions" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "prescriptions", "status", "TEXT")

    # این ستون‌ها به‌اشتباه روی جدول reviews ساخته شده بودند؛ در صورت وجود پاک می‌شوند.
    if "reviews" in table_names:
        with engine.connect() as conn:
            for column, _ in EMERGENCY_CONTACT_COLUMNS:
                _drop_column_if_exists(conn, "reviews", column)


def init_db():
    from app import models  # noqa
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()