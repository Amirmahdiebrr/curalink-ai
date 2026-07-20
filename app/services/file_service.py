"""
File handling service.

Responsibilities:
- Validate uploaded file content
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