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

# کتابخانه‌هایی که با سطح DEBUG/INFO بیش‌ازحد پرحرف هستند و باید
# روی WARNING محدود شوند تا کنسول سرور با جزئیات بی‌ربط شلوغ نشود.
# نکته‌ی مهم: چون این کتابخانه‌ها زیرشاخه‌های زیادی دارند (مثلاً
# fontTools.subset، fontTools.ttLib.ttFont و...)، باید هم لاگر
# اصلی و هم زیرشاخه‌هایش را جداگانه ساکت کنیم؛ صرفاً ساکت‌کردن
# لاگر والد (مثلاً "fontTools") سطح لاگرهای فرزند را override نمی‌کند
# اگر آن فرزندها سطح خودشان را جداگانه ست کرده باشند.
_NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "fontTools",
    "fontTools.subset",
    "fontTools.subset.timer",
    "fontTools.ttLib",
    "fontTools.ttLib.ttFont",
    "weasyprint",
    "weasyprint.progress",
]


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

    # کتابخانه‌های پرحرف را ساکت‌تر می‌کنیم تا لاگ‌های خودمان گم نشوند.
    # این کار هر بار که یک PDF (برنامه غذایی/ورزشی/گزارش آزمایش) با
    # WeasyPrint ساخته می‌شود اهمیت دارد، چون فرآیند subset کردن فونت
    # Vazirmatn توسط fontTools صدها خط لاگ DEBUG درباره‌ی جدول‌های
    # داخلی فونت (glyf، cmap، post و...) تولید می‌کند که کاملاً
    # بی‌خطر است ولی کنسول سرور را غیرقابل‌خواندن می‌کند.
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)