"""
scripts/migrate_sqlite_to_postgres.py

انتقال داده‌ی موجود از SQLite به PostgreSQL بدون نیاز به ابزار
خارجی (pgloader). ابتدا جدول‌ها باید با alembic upgrade head روی
PostgreSQL ساخته شده باشند؛ این اسکریپت فقط رکوردها را کپی می‌کند.

اجرا:
    set SQLITE_PATH=data/lab_analyzer.db
    set POSTGRES_URL=postgresql://curalink:change_this_password@localhost:5432/curalink
    python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, MetaData, Table, insert, select

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/lab_analyzer.db")
POSTGRES_URL = os.getenv("POSTGRES_URL")

if not POSTGRES_URL:
    print("❌ متغیر محیطی POSTGRES_URL تنظیم نشده است.")
    sys.exit(1)

sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
postgres_engine = create_engine(POSTGRES_URL)

# ترتیب مهم است: جدول‌های والد باید قبل از جدول‌های فرزند پر شوند
# تا محدودیت‌های foreign key در PostgreSQL خطا ندهند.
TABLE_ORDER = [
    "users",
    "doctor_profiles",
    "organization_profiles",
    "family_members",
    "plans",
    "service_pricing",
    "subscriptions",
    "payments",
    "analysis_records",
    "test_results",
    "diet_plan_records",
    "visit_prep_records",
    "workout_plan_records",
    "verification_codes",
    "doctor_payouts",
    "organization_members",
    "jobs",
    "generic_jobs",
    "pending_actions",
    "reviews",
    "doctor_notes",
    "prescriptions",
    "prescription_items",
    "patient_followups",
]

# ==========================
# مقادیر پیش‌فرض برای ستون‌هایی که در دیتابیس قدیمی SQLite ممکن است
# NULL باشند (چون آن ستون بعداً به مدل اضافه شده)، ولی در PostgreSQL
# محدودیت NOT NULL دارند. کلید بیرونی = نام جدول، کلید داخلی = نام
# ستون، مقدار = چیزی که باید جایگزین NULL شود.
# ==========================
NOT_NULL_DEFAULTS = {
    "analysis_records": {
        "price_mismatch_flag": False,
    },
    "users": {
        "unlimited_access": False,
        "phone_verified": False,
        "email_verified": False,
        "is_active": True,
    },
    "test_results": {
        "followup_reminder_sent": False,
    },
    "patient_followups": {
        "reminder_sent": False,
    },
}


def _fix_row(table_name: str, row_dict: dict) -> dict:
    defaults = NOT_NULL_DEFAULTS.get(table_name)

    if not defaults:
        return row_dict

    for column, default_value in defaults.items():
        if row_dict.get(column) is None:
            row_dict[column] = default_value

    return row_dict


def migrate_table(table_name: str, sqlite_meta: MetaData, postgres_meta: MetaData):
    if table_name not in sqlite_meta.tables:
        print(f"⚠️  جدول '{table_name}' در SQLite پیدا نشد، رد می‌شود.")
        return

    if table_name not in postgres_meta.tables:
        print(f"⚠️  جدول '{table_name}' در PostgreSQL پیدا نشد (آیا alembic upgrade head را زده‌اید؟)، رد می‌شود.")
        return

    sqlite_table = sqlite_meta.tables[table_name]
    postgres_table = postgres_meta.tables[table_name]

    with sqlite_engine.connect() as sconn, postgres_engine.begin() as pconn:
        rows = sconn.execute(select(sqlite_table)).mappings().all()

        if not rows:
            print(f"ℹ️  جدول '{table_name}': هیچ رکوردی برای انتقال نیست.")
            return

        fixed_rows = [_fix_row(table_name, dict(row)) for row in rows]

        pconn.execute(insert(postgres_table), fixed_rows)
        print(f"✅ جدول '{table_name}': {len(fixed_rows)} رکورد منتقل شد.")


def main():
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    postgres_meta = MetaData()
    postgres_meta.reflect(bind=postgres_engine)

    for table_name in TABLE_ORDER:
        migrate_table(table_name, sqlite_meta, postgres_meta)

    print("\n🎉 انتقال داده به پایان رسید.")


if __name__ == "__main__":
    main()