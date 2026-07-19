"""
app/utils/validators.py

Validation utilities.
"""

from pathlib import Path

from fastapi import UploadFile

from app.core.constants import (
    ALLOWED_FILE_EXTENSIONS,
    MAX_UPLOAD_SIZE_MB,
)

from app.core.exceptions import FileValidationError


class Validators:

    @staticmethod
    def validate_upload(
        file: UploadFile,
    ) -> None:

        if not file.filename:
            raise FileValidationError(
                "نام فایل معتبر نیست."
            )

        extension = Path(
            file.filename
        ).suffix.lower()

        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise FileValidationError(
                "فرمت فایل پشتیبانی نمی‌شود."
            )

        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        max_size = (
            MAX_UPLOAD_SIZE_MB
            * 1024
            * 1024
        )

        if size > max_size:
            raise FileValidationError(
                f"حداکثر حجم فایل {MAX_UPLOAD_SIZE_MB}MB است."
            )