"""
app/services/file/file_validator.py
"""

from pathlib import Path

from app.core.constants import (
    ALLOWED_FILE_EXTENSIONS,
)


class FileValidator:

    @staticmethod
    def validate(
        filename: str,
    ):

        extension = Path(
            filename
        ).suffix.lower()

        if extension not in ALLOWED_FILE_EXTENSIONS:

            raise ValueError(
                f"Unsupported file type: {extension}"
            )

        return extension