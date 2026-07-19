"""
app/services/wp_auth_service.py

Authenticates users against the main WordPress site (curalinkcare.com)
via the JWT Authentication for WP REST API plugin, instead of
maintaining a separate local user database.
"""

import os
import httpx

WORDPRESS_JWT_URL = os.getenv(
    "WORDPRESS_JWT_URL",
    "https://curalinkcare.com/wp-json/jwt-auth/v1/token"
)

WORDPRESS_VALIDATE_URL = os.getenv(
    "WORDPRESS_VALIDATE_URL",
    "https://curalinkcare.com/wp-json/jwt-auth/v1/token/validate"
)

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
}

DEFAULT_ERROR_MESSAGE = "نام کاربری یا رمز عبور اشتباه است."


class WPAuthError(Exception):
    pass


async def login_with_wordpress(username: str, password: str) -> dict:

    print("[WPAuth] Trying login for username:", username, flush=True)
    print("[WPAuth] URL:", WORDPRESS_JWT_URL, flush=True)

    payload = {"username": username, "password": password}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                WORDPRESS_JWT_URL,
                json=payload,
                headers=REQUEST_HEADERS,
            )
    except Exception as e:
        print("[WPAuth] Connection error:", repr(e), flush=True)
        raise WPAuthError("خطا در اتصال به سرور ورود") from e

    print("[WPAuth] Response status:", response.status_code, flush=True)
    print("[WPAuth] Response body:", response.text[:500], flush=True)

    if response.status_code != 200:
        try:
            data = response.json()
            message = data.get("message", DEFAULT_ERROR_MESSAGE)
        except Exception:
            message = DEFAULT_ERROR_MESSAGE
        raise WPAuthError(message)

    data = response.json()

    return {
        "token": data.get("token"),
        "email": data.get("user_email"),
        "nicename": data.get("user_nicename"),
        "display_name": data.get("user_display_name"),
    }


async def validate_token(token: str) -> bool:

    headers = dict(REQUEST_HEADERS)
    headers["Authorization"] = "Bearer " + token

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(WORDPRESS_VALIDATE_URL, headers=headers)
    except Exception:
        return False

    return response.status_code == 200