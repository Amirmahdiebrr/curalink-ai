"""
app/schemas/upload_response.py

Upload response schema.
"""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    filename: str