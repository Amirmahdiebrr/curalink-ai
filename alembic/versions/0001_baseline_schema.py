"""baseline schema (matches existing create_all output)

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00

این migration فقط برای مستندسازی نقطه‌ی شروع است. چون دیتابیس‌های
development/production موجود از قبل با Base.metadata.create_all
ساخته شده‌اند، این فایل را روی آن‌ها اجرا نکنید — به‌جایش:

    alembic stamp 0001

را بزنید تا Alembic بداند این نسخه از قبل اعمال شده. برای دیتابیس
کاملاً تازه (فایل .db وجود ندارد)، از app.database.init_db() طبق
روال قبلی استفاده کنید و سپس همان stamp را بزنید؛ migration‌های
بعدی را از این نقطه با alembic upgrade head اجرا کنید.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # عمداً خالی — جدول‌ها از طریق app.database.init_db() ساخته
    # می‌شوند. این نسخه صرفاً یک نقطه‌ی مرجع (baseline) برای
    # migration‌های بعدی است.
    pass


def downgrade() -> None:
    pass