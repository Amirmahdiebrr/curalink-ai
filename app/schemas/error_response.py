"""
app/schemas/error_response.py

Standard API error schema.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str