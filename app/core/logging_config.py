"""
app/core/logging_config.py

پیکربندی مرکزی logging برای کل پروژه.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# پیشوند نام لاگرهایی که باید زیر WARNING ساکت شوند. این فیلتر روی
# خودِ handler اعمال می‌شود (نه فقط logger.setLevel)، چون fontTools
# هنگام subset کردن فونت (هر بار تولید PDF با WeasyPrint) سطح لاگر
# داخلی خودش را دوباره روی DEBUG/INFO تنظیم می‌کند و ست‌کردن سطح
# logger از قبل را دور می‌زند. فیلتر روی handler، صرف‌نظر از این‌که
# کتابخانه چه سطحی برای logger خودش انتخاب کند، خروجی نهایی را کنترل
# می‌کند.
_NOISY_LOGGER_PREFIXES = [
    "httpx",
    "httpcore",
    "fontTools",
    "weasyprint",
]

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

# مسیرهایی که به‌خاطر polling مکرر هر ۱.۵ ثانیه از صفحات پردازش
# (processing/generic-processing) کنسول را با صدها خط تکراری بی‌فایده
# پر می‌کنند.
_QUIET_ACCESS_PATH_MARKERS = (
    "/status/",
    "/job-status/",
)


class _NoisyLoggerFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for prefix in _NOISY_LOGGER_PREFIXES:
            if record.name == prefix or record.name.startswith(prefix + "."):
                return record.levelno >= logging.WARNING
        return True


class _QuietAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        return not any(marker in message for marker in _QUIET_ACCESS_PATH_MARKERS)


def setup_logging(level: str = "INFO"):
    """
    باید فقط یک‌بار، در main.py و در ابتدای اجرای برنامه صدا زده شود.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler.addFilter(_NoisyLoggerFilter())

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )

    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").addFilter(_QuietAccessFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)