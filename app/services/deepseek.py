import asyncio
import time
import httpx

from app.config import NVIDIA_API_KEY, AI_MODEL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

PRIMARY_MODEL = AI_MODEL

MAX_TOKENS = 4096
READ_TIMEOUT_SECONDS = 60

# محدودیت "Worker local total request limit" مربوط به کل اکانت است،
# نه یک مدل خاص؛ پس به‌جای سوییچ مدل، چند بار با فاصله‌ی زمانی
# افزایشی (backoff) دوباره تلاش می‌کنیم تا ظرفیت آزاد شود.
RETRY_WAITS = [10, 20, 40, 60]  # ثانیه، بین تلاش‌ها


class DeepSeekError(Exception):
    pass


async def _call_model(prompt: str, attempt: int) -> str | None:

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": PRIMARY_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": MAX_TOKENS,
    }

    timeout = httpx.Timeout(connect=15, read=READ_TIMEOUT_SECONDS, write=15, pool=15)

    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(NVIDIA_URL, headers=headers, json=payload)
    except (httpx.TimeoutException, httpx.ReadError, httpx.ConnectError) as e:
        elapsed = time.perf_counter() - start
        logger.warning(f"[DeepSeek] Attempt {attempt}: network error {repr(e)} [{elapsed:.2f}s]")
        return None

    elapsed = time.perf_counter() - start
    logger.info(f"[DeepSeek] Attempt {attempt}: status={response.status_code} [{elapsed:.2f}s]")

    if response.status_code == 200:
        data = response.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]

        if choice.get("finish_reason") == "length":
            logger.warning(f"[DeepSeek] Response cut off due to max_tokens={MAX_TOKENS}")

        return content

    if response.status_code in (503, 429):
        logger.warning(f"[DeepSeek] Attempt {attempt}: busy ({response.status_code}): {response.text[:300]}")
        return None

    logger.error(f"[DeepSeek] Attempt {attempt}: error {response.status_code}: {response.text[:500]}")
    raise DeepSeekError(f"خطای {response.status_code}: {response.text[:300]}")


async def ask_ai(prompt: str) -> str:

    total_attempts = len(RETRY_WAITS) + 1

    for attempt in range(1, total_attempts + 1):
        result = await _call_model(prompt, attempt)

        if result is not None:
            return result

        if attempt <= len(RETRY_WAITS):
            wait = RETRY_WAITS[attempt - 1]
            logger.info(f"[DeepSeek] Waiting {wait}s before attempt {attempt + 1}/{total_attempts}")
            await asyncio.sleep(wait)

    raise DeepSeekError(
        "سرویس هوش مصنوعی در حال حاضر بسیار شلوغ است. لطفاً چند دقیقه دیگر دوباره امتحان کنید."
    )