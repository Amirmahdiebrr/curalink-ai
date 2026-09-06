"""
app/database.py
"""

from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_IS_SQLITE = DATABASE_URL.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _IS_SQLITE else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=not _IS_SQLITE,  # اتصال‌های مرده به PostgreSQL را قبل از استفاده تشخیص می‌دهد
)


if _IS_SQLITE:
    @event.listens_for(Engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """
        در SQLite، اعمال محدودیت‌های foreign key به‌صورت پیش‌فرض خاموش
        است و باید روی هر اتصال جداگانه فعال شود. PostgreSQL این
        محدودیت‌ها را همیشه به‌صورت پیش‌فرض اعمال می‌کند، پس این
        event فقط برای SQLite ثبت می‌شود.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
# NOTE — Migration strategy
#
# از این پس، هر تغییر جدید در ساختار دیتابیس (ستون/جدول جدید، تغییر
# نوع، حذف ستون) باید با یک فایل Alembic migration در alembic/versions
# نوشته شود (دستور: alembic revision --autogenerate -m "توضیح").
# توابع زیر (_add_column_if_missing و _run_light_migrations) روی هر
# دو دیتابیس (SQLite و PostgreSQL) اجرا می‌شوند تا اگر یک دیتابیس
# (مثلاً یک volume تازه‌ی PostgreSQL در داکر) بدون عبور از Alembic
# ساخته شده باشد، ستون‌های جدیدی که به مدل‌ها اضافه شده‌اند خودکار
# ساخته شوند و برنامه با خطای "column does not exist" کرش نکند.
# ==========================


def _bool_default_literal(value: bool) -> str:
    if _IS_SQLITE:
        return "1" if value else "0"
    return "true" if value else "false"


def _add_column_if_missing(conn, table: str, column: str, ddl_type: str):
    inspector = inspect(engine)

    if table not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns(table)}

    if column not in existing_columns:
        logger.info(f"[DB Migration] Adding missing column '{column}' to {table}...")
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        conn.commit()
        logger.info(f"[DB Migration] Column '{column}' added successfully to {table}.")


def _drop_column_if_exists(conn, table: str, column: str):
    inspector = inspect(engine)

    if table not in inspector.get_table_names():
        return

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

    datetime_type = "DATETIME" if _IS_SQLITE else "TIMESTAMP"

    unlimited_access_columns = [
        ("unlimited_access", f"BOOLEAN DEFAULT {_bool_default_literal(False)}"),
        ("unlimited_access_granted_by", "INTEGER"),
        ("unlimited_access_granted_at", datetime_type),
    ]

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
            _add_column_if_missing(conn, "analysis_records", "requested_exam_type", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "price_paid", "INTEGER")
            _add_column_if_missing(conn, "analysis_records", "price_mismatch_flag", f"BOOLEAN DEFAULT {_bool_default_literal(False)}")
            _add_column_if_missing(conn, "analysis_records", "price_mismatch_amount", "INTEGER")
            _add_column_if_missing(conn, "analysis_records", "series_id", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "updated_at", datetime_type)

    if "test_results" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "test_results", "family_member_id", "INTEGER")
            _add_column_if_missing(conn, "test_results", "recommended_followup_days", "INTEGER")
            _add_column_if_missing(conn, "test_results", "organ_category", "TEXT")
            _add_column_if_missing(conn, "test_results", "followup_reminder_sent", f"BOOLEAN DEFAULT {_bool_default_literal(False)}")

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
            for column, ddl_type in unlimited_access_columns:
                _add_column_if_missing(conn, "users", column, ddl_type)
            _add_column_if_missing(conn, "users", "updated_at", datetime_type)
            _add_column_if_missing(conn, "users", "profile_notice_seen", f"BOOLEAN DEFAULT {_bool_default_literal(False)}")

    if "family_members" in table_names:
        with engine.connect() as conn:
            for column, ddl_type in HEALTH_PROFILE_COLUMNS:
                _add_column_if_missing(conn, "family_members", column, ddl_type)

    if "prescriptions" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "prescriptions", "status", "TEXT")
            _add_column_if_missing(conn, "prescriptions", "updated_at", datetime_type)

    if "payments" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "payments", "updated_at", datetime_type)

    if "subscriptions" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "subscriptions", "updated_at", datetime_type)

    if "patient_followups" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "patient_followups", "reminder_sent", f"BOOLEAN DEFAULT {_bool_default_literal(False)}")

    # این ستون‌ها به‌اشتباه روی جدول reviews ساخته شده بودند؛ در صورت وجود پاک می‌شوند.
    if "reviews" in table_names:
        with engine.connect() as conn:
            for column, _ in EMERGENCY_CONTACT_COLUMNS:
                _drop_column_if_exists(conn, "reviews", column)


def init_db():
    from app import models  # noqa
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()