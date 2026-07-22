"""
app/database.py

SQLAlchemy database setup (SQLite file-based).
"""

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./lab_analyzer.db"

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
        print(f"[DB Migration] Adding missing column '{column}' to {table}...", flush=True)
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        conn.commit()
        print(f"[DB Migration] Column '{column}' added successfully to {table}.", flush=True)


def _run_light_migrations():
    """
    Adds newly-introduced columns to existing SQLite tables that were
    created before this project used a proper migration tool (Alembic).
    Safe to call every startup: it only adds a column if it's missing.
    New tables are created automatically by Base.metadata.create_all()
    before this function runs.
    """

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "local_users" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "local_users", "phone", "TEXT")

    if "analysis_records" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "analysis_records", "symptoms", "TEXT")
            _add_column_if_missing(conn, "analysis_records", "family_member_id", "INTEGER")

    if "test_results" in table_names:
        with engine.connect() as conn:
            _add_column_if_missing(conn, "test_results", "family_member_id", "INTEGER")
            _add_column_if_missing(conn, "test_results", "recommended_followup_days", "INTEGER")
            _add_column_if_missing(conn, "test_results", "organ_category", "TEXT")
            _add_column_if_missing(conn, "test_results", "followup_reminder_sent", "BOOLEAN DEFAULT 0")


def init_db():
    from app import models  # noqa
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()