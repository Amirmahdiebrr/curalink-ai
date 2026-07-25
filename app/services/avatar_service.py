"""
app/services/avatar_service.py

اعتبارسنجی و ذخیره‌ی عکس پروفایل کاربران (بیمار/پزشک/سازمان/ادمین).

مسئولیت‌ها:
- بررسی پسوند مجاز فایل
- بررسی حجم مجاز فایل
- بررسی مطابقت امضای واقعی بایت‌های فایل با پسوند اعلام‌شده (همان
  منطقی که file_service.py برای فایل‌های آزمایش استفاده می‌کند)
- ذخیره‌ی فایل روی دیسک، داخل مسیر استاتیک برنامه، تا از طریق
  StaticFiles (/static/...) مستقیماً در تگ <img> قابل نمایش باشد
"""

import uuid
from pathlib import Path

from app.config import AVATAR_MAX_SIZE_MB, AVATAR_ALLOWED_EXTENSIONS
from app.services.file_service import signature_matches_extension
from app.core.logging_config import get_logger

logger = get_logger(__name__)

AVATAR_DIR = Path("app/static/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)


class AvatarError(Exception):
    """
    خطای مربوط به اعتبارسنجی یا ذخیره‌سازی عکس پروفایل.
    """
    pass


def save_avatar(content: bytes, filename: str) -> str:
    """
    فایل عکس پروفایل را اعتبارسنجی و روی دیسک ذخیره می‌کند.

    Parameters
    ----------
    content : bytes
        محتوای خام فایل آپلودشده.
    filename : str
        نام اصلی فایل (برای تشخیص پسوند).

    Returns
    -------
    str
        مسیر وب قابل استفاده در <img src="...">، مثلاً:
        "/static/avatars/3f9a1c2e....png"
        (نه مسیر فیزیکی روی دیسک)

    Raises
    ------
    AvatarError
        اگر فایل خالی باشد، پسوند مجاز نباشد، حجم بیش از حد مجاز باشد،
        یا محتوای واقعی فایل با پسوند اعلام‌شده مطابقت نداشته باشد.
    """

    if not filename:
        raise AvatarError("نام فایل ارسال نشده است.")

    if not content:
        raise AvatarError("فایل عکس خالی است.")

    extension = Path(filename).suffix.lower()

    if extension not in AVATAR_ALLOWED_EXTENSIONS:
        raise AvatarError("فرمت فایل مجاز نیست. فقط PNG یا JPG مجاز است.")

    size_mb = len(content) / (1024 * 1024)

    if size_mb > AVATAR_MAX_SIZE_MB:
        raise AvatarError(f"حجم فایل نباید بیشتر از {AVATAR_MAX_SIZE_MB} مگابایت باشد.")

    if not signature_matches_extension(extension, content):
        raise AvatarError("محتوای فایل با پسوند اعلام‌شده مطابقت ندارد.")

    unique_name = f"{uuid.uuid4().hex}{extension}"
    filepath = AVATAR_DIR / unique_name

    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"[AvatarService] Failed to save avatar file: {e}")
        raise AvatarError("ذخیره‌سازی عکس پروفایل با خطا مواجه شد.")

    return f"/static/avatars/{unique_name}"