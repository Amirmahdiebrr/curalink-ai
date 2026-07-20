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


def _run_light_migrations():
    """
    Adds newly-introduced columns to existing SQLite tables that were
    created before this project used a proper migration tool (Alembic).
    Safe to call every startup: it only adds a column if it's missing.
    """

    inspector = inspect(engine)

    if "analysis_records" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("analysis_records")}

    if "symptoms" not in existing_columns:
        print("[DB Migration] Adding missing column 'symptoms' to analysis_records...", flush=True)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE analysis_records ADD COLUMN symptoms TEXT"))
            conn.commit()
        print("[DB Migration] Column 'symptoms' added successfully.", flush=True)


def init_db():
    from app import models  # noqa
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()