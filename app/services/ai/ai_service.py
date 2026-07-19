from openai import OpenAI

from app.config.ai_settings import AISettings


class AIService:

    def __init__(self):

        self.settings = AISettings.load()

        self.client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )

    def analyze(self, prompt: str) -> str:

        response = self.client.chat.completions.create(

            model=self.settings.model,

            messages=[
                {
                    "role": "system",
                    "content": "You are a professional medical laboratory analyzer."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.2,
            max_tokens=2500,

        )

        return response.choices[0].message.content

    # برای سازگاری با فایل‌های قدیمی پروژه
    def ask(self, prompt: str) -> str:
        return self.analyze(prompt)