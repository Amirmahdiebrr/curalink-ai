import re


class TextUtils:

    @staticmethod
    def normalize(text: str) -> str:

        text = text.replace("\r", "")

        text = re.sub(
            r"\n+",
            "\n",
            text,
        )

        return text.strip()