from dotenv import load_dotenv
import os


load_dotenv()


DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY"
)


if not DEEPSEEK_API_KEY:
    print(
        "WARNING: DEEPSEEK_API_KEY not loaded"
    )