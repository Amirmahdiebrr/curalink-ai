import asyncio
import time
import httpx

from app.config import NVIDIA_API_KEY, AI_MODEL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MAX_TOKENS = 6000


class DeepSeekError(Exception):
    pass


async def ask_ai(prompt: str) -> str:

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": MAX_TOKENS,
    }

    timeout = httpx.Timeout(connect=15, read=280, write=15, pool=15)

    max_attempts = 2

    async with httpx.AsyncClient(timeout=timeout) as client:

        for attempt in range(1, max_attempts + 1):

            attempt_start = time.perf_counter()

            logger.info(f"[DeepSeek] Attempt {attempt}/{max_attempts}")

            try:
                response = await client.post(
                    NVIDIA_URL,
                    headers=headers,
                    json=payload
                )

            except (httpx.TimeoutException, httpx.ReadError, httpx.ConnectError) as e:
                elapsed = time.perf_counter() - attempt_start
                wait = 5
                logger.warning(f"[DeepSeek] Network error on attempt {attempt}: {repr(e)}  [{elapsed:.2f}s] -> waiting {wait}s")
                if attempt == max_attempts:
                    raise DeepSeekError("درخواست به NVIDIA API با تایم‌اوت مواجه شد. سرویس احتمالاً موقتاً کند است، لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
                await asyncio.sleep(wait)
                continue

            except Exception as e:
                logger.error(f"[DeepSeek] Unexpected request error: {repr(e)}")
                raise DeepSeekError(str(e))

            elapsed = time.perf_counter() - attempt_start

            logger.info(f"[DeepSeek] Response status: {response.status_code}  [{elapsed:.2f}s]")

            if response.status_code == 200:
                data = response.json()
                choice = data["choices"][0]
                finish_reason = choice.get("finish_reason")
                content = choice["message"]["content"]

                if finish_reason == "length":
                    logger.warning(
                        f"[DeepSeek] WARNING: response cut off due to max_tokens={MAX_TOKENS}. "
                        f"Attempt {attempt}/{max_attempts}. Content length so far: {len(content)}"
                    )

                    if attempt == max_attempts:
                        # پاسخ قطع‌شده را برمی‌گردانیم (بهتر از هیچ) اما با
                        # پرچم مشخص در لاگ، چون این احتمالاً بلوک JSON انتهایی
                        # گزارش را خراب می‌کند.
                        logger.warning("[DeepSeek] Returning truncated content after final attempt.")
                        return content

                    logger.info("[DeepSeek] Retrying once in hope of a complete response...")
                    await asyncio.sleep(2)
                    continue

                return content

            if response.status_code in (503, 429):
                wait = 10
                logger.warning(f"[DeepSeek] NVIDIA busy ({response.status_code}): {response.text[:300]} -> waiting {wait}s")
                if attempt == max_attempts:
                    raise DeepSeekError("سرویس NVIDIA در حال حاضر شلوغ است (ظرفیت پر شده). لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
                await asyncio.sleep(wait)
                continue

            logger.error(f"[DeepSeek] Error response {response.status_code}: {response.text[:500]}")
            raise DeepSeekError(f"خطای {response.status_code}: {response.text[:300]}")

    raise DeepSeekError("سرویس هوش مصنوعی در دسترس نیست (پس از چند تلاش).")