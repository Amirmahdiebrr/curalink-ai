"""
app/core/logging_config.py

پیکربندی مرکزی logging برای کل پروژه. جایگزین print() های پراکنده.
هر فایل با `logger = get_logger(__name__)` یک logger مخصوص خودش می‌گیرد
که نام ماژول در ابتدای هر خط لاگ نمایش داده می‌شود.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO"):
    """
    باید فقط یک‌بار، در main.py و در ابتدای اجرای برنامه صدا زده شود.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # کتابخانه‌های پرحرف را ساکت‌تر می‌کنیم تا لاگ‌های خودمان گم نشوند
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)