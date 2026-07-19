"""
File handling service.

Responsibilities:
- Validate uploaded file content
- Save uploaded file bytes to disk
"""

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


class FileService:
    """
    Handles uploaded medical files.
    """

    @staticmethod
    def validate_bytes(filename: str, content: bytes):

        if not filename:
            raise FileValidationError("File name is empty.")

        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise FileValidationError("File extension is not supported.")

        file_size_mb = len(content) / (1024 * 1024)

        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            raise FileValidationError("File size is too large.")

        return True

    @staticmethod
    def save_bytes(filename: str, content: bytes) -> Path:
        """
        Validate and save raw file bytes to the uploads directory.
        """
        FileService.validate_bytes(filename, content)

        filepath = UPLOAD_DIR / filename

        with open(filepath, "wb") as buffer:
            buffer.write(content)

        return filepath