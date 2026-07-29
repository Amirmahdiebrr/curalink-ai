"""
app/services/deepseek.py

لایه‌ی ارتباط با هوش مصنوعی از طریق API گپ‌جی‌پی‌تی (GapGPT) — سازگار
با فرمت رسمی OpenAI. جایگزین تماس مستقیم قبلی به NVIDIA.
"""

import asyncio
import time

from openai import AsyncOpenAI, APIStatusError, APIConnectionError, APITimeoutError

from app.config import GAPGPT_API_KEY, GAPGPT_BASE_URL, AI_MODEL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PRIMARY_MODEL = AI_MODEL

MAX_TOKENS = 8192
READ_TIMEOUT_SECONDS = 60

# در صورت شلوغی/خطای موقت سرویس، چند بار با فاصله‌ی زمانی افزایشی
# (backoff) دوباره تلاش می‌کنیم به‌جای شکست کامل درخواست.
RETRY_WAITS = [10, 20, 40, 60]  # ثانیه، بین تلاش‌ها


class DeepSeekError(Exception):
    pass


_client = AsyncOpenAI(
    base_url=GAPGPT_BASE_URL,
    api_key=GAPGPT_API_KEY,
    timeout=READ_TIMEOUT_SECONDS,
)


async def _call_model(prompt: str, attempt: int) -> str | None:

    start = time.perf_counter()

    try:
        response = await _client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=MAX_TOKENS,
        )

    except (APIConnectionError, APITimeoutError) as e:
        elapsed = time.perf_counter() - start
        logger.warning(f"[GapGPT] Attempt {attempt}: network error {repr(e)} [{elapsed:.2f}s]")
        return None

    except APIStatusError as e:
        elapsed = time.perf_counter() - start

        if e.status_code in (503, 429):
            logger.warning(f"[GapGPT] Attempt {attempt}: busy ({e.status_code}) [{elapsed:.2f}s]: {e.response.text[:300]}")
            return None

        logger.error(f"[GapGPT] Attempt {attempt}: error {e.status_code} [{elapsed:.2f}s]: {e.response.text[:500]}")
        raise DeepSeekError(f"خطای {e.status_code}: {e.response.text[:300]}")

    elapsed = time.perf_counter() - start
    logger.info(f"[GapGPT] Attempt {attempt}: success [{elapsed:.2f}s]")

    choice = response.choices[0]
    content = choice.message.content

    if choice.finish_reason == "length":
        logger.warning(f"[GapGPT] Response cut off due to max_tokens={MAX_TOKENS}")

    return content


async def ask_ai(prompt: str) -> str:

    total_attempts = len(RETRY_WAITS) + 1

    for attempt in range(1, total_attempts + 1):
        result = await _call_model(prompt, attempt)

        if result is not None:
            return result

        if attempt <= len(RETRY_WAITS):
            wait = RETRY_WAITS[attempt - 1]
            logger.info(f"[GapGPT] Waiting {wait}s before attempt {attempt + 1}/{total_attempts}")
            await asyncio.sleep(wait)

    raise DeepSeekError(
        "سرویس هوش مصنوعی در حال حاضر بسیار شلوغ است. لطفاً چند دقیقه دیگر دوباره امتحان کنید."
    )