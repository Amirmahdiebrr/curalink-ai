import asyncio
import time
import httpx

from app.config import NVIDIA_API_KEY, AI_MODEL


NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


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
        "max_tokens": 6000,
    }

    timeout = httpx.Timeout(connect=15, read=280, write=15, pool=15)

    max_attempts = 3

    async with httpx.AsyncClient(timeout=timeout) as client:

        for attempt in range(1, max_attempts + 1):

            attempt_start = time.perf_counter()

            print(f"[DeepSeek] Attempt {attempt}/{max_attempts}", flush=True)

            try:
                response = await client.post(
                    NVIDIA_URL,
                    headers=headers,
                    json=payload
                )

            except (httpx.TimeoutException, httpx.ReadError, httpx.ConnectError) as e:
                elapsed = time.perf_counter() - attempt_start
                wait = min(5 * (2 ** (attempt - 1)), 30)
                print(f"[DeepSeek] Network error on attempt {attempt}: {repr(e)}  [{elapsed:.2f}s] -> waiting {wait}s", flush=True)
                if attempt == max_attempts:
                    raise DeepSeekError("درخواست به NVIDIA API با تایم‌اوت/خطای شبکه مواجه شد. سرویس احتمالاً موقتاً شلوغ است، لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
                await asyncio.sleep(wait)
                continue

            except Exception as e:
                print(f"[DeepSeek] Unexpected request error: {repr(e)}", flush=True)
                raise DeepSeekError(str(e))

            elapsed = time.perf_counter() - attempt_start

            print(f"[DeepSeek] Response status: {response.status_code}  [{elapsed:.2f}s]", flush=True)

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            if response.status_code in (503, 429):
                wait = min(5 * (2 ** (attempt - 1)), 30)
                print(f"[DeepSeek] NVIDIA busy ({response.status_code}): {response.text[:300]} -> waiting {wait}s", flush=True)
                if attempt == max_attempts:
                    raise DeepSeekError("سرویس NVIDIA در حال حاضر شلوغ است (ظرفیت پر شده). لطفاً چند دقیقه دیگر دوباره امتحان کنید.")
                await asyncio.sleep(wait)
                continue

            print(f"[DeepSeek] Error response {response.status_code}: {response.text[:500]}", flush=True)
            raise DeepSeekError(f"خطای {response.status_code}: {response.text[:300]}")

    raise DeepSeekError("سرویس هوش مصنوعی در دسترس نیست (پس از چند تلاش).")