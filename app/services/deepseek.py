import asyncio
import time
import httpx

from app.config import NVIDIA_API_KEY, AI_MODEL, AI_FALLBACK_MODEL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MAX_TOKENS = 6000


class DeepSeekError(Exception):
    pass


async def _call_model(client: httpx.AsyncClient, model: str, prompt: str, max_attempts: int, label: str) -> str:
    """
    یک مدل مشخص را حداکثر `max_attempts` بار امتحان می‌کند. در صورت
    موفقیت متن پاسخ را برمی‌گرداند؛ در غیر این صورت DeepSeekError
    (برای شکست نهایی) پرتاب می‌کند.
    """

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": MAX_TOKENS,
    }

    for attempt in range(1, max_attempts + 1):

        attempt_start = time.perf_counter()

        logger.info(f"[DeepSeek][{label}] Attempt {attempt}/{max_attempts} (model={model})")

        try:
            response = await client.post(
                NVIDIA_URL,
                headers=headers,
                json=payload
            )

        except (httpx.TimeoutException, httpx.ReadError, httpx.ConnectError) as e:
            elapsed = time.perf_counter() - attempt_start
            wait = 5
            logger.warning(f"[DeepSeek][{label}] Network error on attempt {attempt}: {repr(e)}  [{elapsed:.2f}s] -> waiting {wait}s")
            if attempt == max_attempts:
                raise DeepSeekError("درخواست به NVIDIA API با تایم‌اوت مواجه شد. سرویس احتمالاً موقتاً کند است، لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
            await asyncio.sleep(wait)
            continue

        except Exception as e:
            logger.error(f"[DeepSeek][{label}] Unexpected request error: {repr(e)}")
            raise DeepSeekError(str(e))

        elapsed = time.perf_counter() - attempt_start

        logger.info(f"[DeepSeek][{label}] Response status: {response.status_code}  [{elapsed:.2f}s]")

        if response.status_code == 200:
            data = response.json()
            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason")
            content = choice["message"]["content"]

            if finish_reason == "length":
                logger.warning(
                    f"[DeepSeek][{label}] WARNING: response cut off due to max_tokens={MAX_TOKENS}. "
                    f"Attempt {attempt}/{max_attempts}. Content length so far: {len(content)}"
                )

                if attempt == max_attempts:
                    # پاسخ قطع‌شده را برمی‌گردانیم (بهتر از هیچ) اما با
                    # پرچم مشخص در لاگ، چون این احتمالاً بلوک JSON انتهایی
                    # گزارش را خراب می‌کند.
                    logger.warning(f"[DeepSeek][{label}] Returning truncated content after final attempt.")
                    return content

                logger.info(f"[DeepSeek][{label}] Retrying once in hope of a complete response...")
                await asyncio.sleep(2)
                continue

            return content

        if response.status_code in (503, 429):
            wait = 10
            logger.warning(f"[DeepSeek][{label}] NVIDIA busy ({response.status_code}): {response.text[:300]} -> waiting {wait}s")
            if attempt == max_attempts:
                raise DeepSeekError("سرویس NVIDIA در حال حاضر شلوغ است (ظرفیت پر شده). لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
            await asyncio.sleep(wait)
            continue

        logger.error(f"[DeepSeek][{label}] Error response {response.status_code}: {response.text[:500]}")
        raise DeepSeekError(f"خطای {response.status_code}: {response.text[:300]}")

    raise DeepSeekError("سرویس هوش مصنوعی در دسترس نیست (پس از چند تلاش).")


async def ask_ai(prompt: str) -> str:
    """
    ابتدا مدل اصلی (AI_MODEL) را امتحان می‌کند. اگر مدل اصلی به‌طور
    کامل شکست بخورد (timeout مکرر یا 503/429 مکرر)، به‌صورت خودکار
    یک بار مدل جایگزین سبک‌تر (AI_FALLBACK_MODEL) را امتحان می‌کند
    تا کاربر با شکست کامل تحلیل مواجه نشود. اگر مدل جایگزین با مدل
    اصلی یکسان باشد یا تعریف نشده باشد، فقط مدل اصلی امتحان می‌شود.
    """

    timeout = httpx.Timeout(connect=15, read=280, write=15, pool=15)

    async with httpx.AsyncClient(timeout=timeout) as client:

        try:
            return await _call_model(client, AI_MODEL, prompt, max_attempts=2, label="primary")

        except DeepSeekError as primary_error:

            if not AI_FALLBACK_MODEL or AI_FALLBACK_MODEL == AI_MODEL:
                raise

            logger.warning(
                f"[DeepSeek] Primary model '{AI_MODEL}' failed ({primary_error}). "
                f"Falling back to '{AI_FALLBACK_MODEL}'..."
            )

            try:
                return await _call_model(client, AI_FALLBACK_MODEL, prompt, max_attempts=1, label="fallback")

            except DeepSeekError as fallback_error:
                logger.error(f"[DeepSeek] Fallback model also failed: {fallback_error}")
                raise DeepSeekError(
                    "سرویس هوش مصنوعی (اصلی و جایگزین) در حال حاضر در دسترس نیست. "
                    "لطفاً چند دقیقه دیگر دوباره امتحان کنید."
                )