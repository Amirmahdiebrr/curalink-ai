"""
scripts/check_i18n_parity.py

بررسی می‌کند که آیا کلیدهای موجود در app/i18n/fa.py و app/i18n/en.py
دقیقاً یکسان هستند یا نه. چون سیستم ترجمه هر کلید گم‌شده در یک زبان
را خاموش به فارسی برمی‌گرداند (fallback)، بدون این بررسی ممکن است
یک صفحه‌ی انگلیسی ناگهان حاوی چند جمله‌ی فارسی باشد بدون این‌که
کسی متوجه شود.

اجرا:
    python scripts/check_i18n_parity.py

خروجی صفر (exit code 0) یعنی کلیدها کاملاً هم‌تراز هستند.
خروجی غیر صفر (exit code 1) یعنی حداقل یک اختلاف پیدا شده و جزئیات
در stdout چاپ می‌شود — مناسب برای استفاده در CI.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.i18n.fa import FA_TRANSLATIONS
from app.i18n.en import EN_TRANSLATIONS


def main() -> int:
    fa_keys = set(FA_TRANSLATIONS.keys())
    en_keys = set(EN_TRANSLATIONS.keys())

    missing_in_en = sorted(fa_keys - en_keys)
    missing_in_fa = sorted(en_keys - fa_keys)

    has_issues = bool(missing_in_en or missing_in_fa)

    if missing_in_en:
        print(f"\n❌ {len(missing_in_en)} کلید در en.py وجود ندارد (و به فارسی fallback می‌شود):\n")
        for key in missing_in_en:
            print(f"  - {key}")

    if missing_in_fa:
        print(f"\n❌ {len(missing_in_fa)} کلید در fa.py وجود ندارد (احتمالاً کلید اضافی/اشتباه در en.py):\n")
        for key in missing_in_fa:
            print(f"  - {key}")

    if not has_issues:
        print(f"✅ هر دو فایل ترجمه دقیقاً {len(fa_keys)} کلید یکسان دارند.")
        return 0

    print(f"\nجمع‌بندی: {len(fa_keys)} کلید در fa.py، {len(en_keys)} کلید در en.py.")
    return 1


if __name__ == "__main__":
    sys.exit(main())