"""
File validation utilities.
"""


from pathlib import Path


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".webp",
}


class FileValidator:


    @staticmethod
    def validate(
        filename: str,
    ) -> bool:

        extension = Path(
            filename
        ).suffix.lower()


        return extension in ALLOWED_EXTENSIONS