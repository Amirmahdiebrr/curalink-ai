"""
alembic/env.py

پیکربندی Alembic برای پروژه‌ی CuraLink. مدل‌های SQLAlchemy از
app.models وارد می‌شوند تا Base.metadata همیشه با آخرین وضعیت مدل‌ها
هماهنگ باشد (برای autogenerate). آدرس دیتابیس از app.config.DATABASE_URL
خوانده می‌شود (نه از alembic.ini)، تا با تنظیمات SQLite/PostgreSQL
واقعی پروژه همیشه یکسان باشد.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base  # noqa: E402
from app.config import DATABASE_URL  # noqa: E402
from app import models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # لازم برای SQLite؛ روی PostgreSQL بی‌ضرر است
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()