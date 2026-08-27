"""
app/core/asset_helpers.py

در حالت production (APP_BASE_URL با https شروع شود)، لینک استایل/اسکریپت
به نسخه‌ی minify‌شده در app/static/dist/ اشاره می‌کند (اگر آن فایل
واقعاً وجود داشته باشد، یعنی build اجرا شده است). در غیر این صورت
(یا اگر فایل build شده پیدا نشود)، به فایل خام توسعه در app/static/css
یا app/static/js فالبک می‌کند تا هیچ‌وقت لینک شکسته نشود.
"""

from pathlib import Path

from app.config import IS_PRODUCTION

STATIC_DIR = Path("app/static")
DIST_DIR = STATIC_DIR / "dist"


def asset_url(relative_path: str) -> str:
    """
    relative_path مثل "css/style.css" یا "js/main.js" را می‌گیرد و
    در حالت production+build-شده مسیر "/static/dist/style.min.css"
    را برمی‌گرداند، وگرنه مسیر خام "/static/css/style.css" را.
    """
    path_obj = Path(relative_path)
    stem = path_obj.stem
    suffix = path_obj.suffix

    min_filename = f"{stem}.min{suffix}"
    min_filepath = DIST_DIR / min_filename

    if IS_PRODUCTION and min_filepath.exists():
        return f"/static/dist/{min_filename}"

    return f"/static/{relative_path}"