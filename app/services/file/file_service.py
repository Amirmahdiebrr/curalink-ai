from pathlib import Path
import shutil
import uuid

from fastapi import UploadFile


class FileService:

    UPLOAD_DIR = Path("uploads")

    ALLOWED = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
    }

    def __init__(self):

        self.UPLOAD_DIR.mkdir(exist_ok=True)

    def save(self, file: UploadFile) -> Path:

        extension = Path(file.filename).suffix.lower()

        if extension not in self.ALLOWED:
            raise Exception("Unsupported file type.")

        filename = f"{uuid.uuid4()}{extension}"

        filepath = self.UPLOAD_DIR / filename

        with open(filepath, "wb") as buffer:

            shutil.copyfileobj(file.file, buffer)

        return filepath