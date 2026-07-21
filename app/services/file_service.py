"""
File handling service.

Responsibilities:
- Validate uploaded file content (extension + actual binary signature)
- Save uploaded file bytes to disk
"""

import uuid
from pathlib import Path

from app.core.constants import (
    MAX_UPLOAD_SIZE_MB,
    ALLOWED_FILE_EXTENSIONS,
)
from app.core.exceptions import (
    FileValidationError,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# امضای بایت‌های ابتدایی هر فرمت مجاز (magic numbers)، برای اطمینان از
# این‌که محتوای واقعی فایل با پسوند اعلام‌شده مطابقت دارد، نه فقط نامش.
def _is_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def _is_png(content: bytes) -> bool:
    return content[:8] == b"\x89PNG\r\n\x1a\n"


def _is_jpeg(content: bytes) -> bool:
    return content[:3] == b"\xff\xd8\xff"


def _is_tiff(content: bytes) -> bool:
    return content[:4] in (b"II*\x00", b"MM\x00*")


def _is_bmp(content: bytes) -> bool:
    return content[:2] == b"BM"


def _is_heic(content: bytes) -> bool:
    # فایل‌های HEIC/HEIF بر پایه‌ی فرمت جعبه‌ای ISOBMFF هستند: چهار بایت
    # اول طول جعبه است، سپس بایت‌های ۴ تا ۸ باید "ftyp" باشد و بعد از آن
    # یکی از برندهای رایج HEIC/HEIF.
    if len(content) < 12:
        return False
    if content[4:8] != b"ftyp":
        return False
    brand = content[8:12]
    known_brands = (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis")
    return brand in known_brands


_SIGNATURE_CHECKS = {
    ".pdf": _is_pdf,
    ".png": _is_png,
    ".jpg": _is_jpeg,
    ".jpeg": _is_jpeg,
    ".tiff": _is_tiff,
    ".bmp": _is_bmp,
    ".heic": _is_heic,
    ".heif": _is_heic,
}


class FileService:
    """
    Handles uploaded medical files.
    """

    @staticmethod
    def validate_bytes(filename: str, content: bytes):

        if not filename:
            raise FileValidationError("File name is empty.")

        if not content:
            raise FileValidationError("Uploaded file is empty.")

        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise FileValidationError("File extension is not supported.")

        file_size_mb = len(content) / (1024 * 1024)

        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            raise FileValidationError("File size is too large.")

        signature_check = _SIGNATURE_CHECKS.get(extension)

        if signature_check and not signature_check(content):
            raise FileValidationError(
                "File content does not match its extension."
            )

        return True

    @staticmethod
    def save_bytes(filename: str, content: bytes) -> Path:
        """
        Validate and save raw file bytes to the uploads directory.
        A random prefix avoids collisions when multiple uploaded
        files share the same original name.
        """
        FileService.validate_bytes(filename, content)

        extension = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{extension}"

        filepath = UPLOAD_DIR / unique_name

        with open(filepath, "wb") as buffer:
            buffer.write(content)

        return filepath