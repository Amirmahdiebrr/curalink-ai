"""
app/services/ai/json_parser.py

Parse AI response into domain models.
"""

import json

from app.schemas.parser import AIResponseParser
from app.utils.json_utils import JsonUtils


class AIJsonParser:
    """
    Parse AI JSON response.
    """

    @classmethod
    def parse(
        cls,
        response: str,
    ):

        try:

            data = JsonUtils.loads(
                response
            )

        except json.JSONDecodeError:

            data = {
                "document_type": "lab_report",
                "title": "Medical Report",
                "summary": response,
                "confidence": 0,
                "findings": [],
                "parameters": [],
                "recommendations": [],
            }

        return AIResponseParser.parse(
            data
        )