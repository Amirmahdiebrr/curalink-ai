"""
app/utils/file_utils.py
"""

from pathlib import Path


class FileUtils:

    @staticmethod
    def extension(
        filename: str,
    ) -> str:

        return Path(
            filename
        ).suffix.lower()


    @staticmethod
    def stem(
        filename: str,
    ) -> str:

        return Path(
            filename
        ).stem