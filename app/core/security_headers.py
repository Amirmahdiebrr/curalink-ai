"""
app/core/security_headers.py

Middleware که هدرهای امنیتی استاندارد را به تمام پاسخ‌های HTTP اضافه
می‌کند: CSP (کنترل منابع مجاز برای اسکریپت/فونت/تصویر/استایل)،
X-Frame-Options (جلوگیری از clickjacking)، X-Content-Type-Options
(جلوگیری از MIME sniffing) و در حالت production، Strict-Transport-
-Security (اجبار HTTPS).

script-src دیگر 'unsafe-inline' ندارد؛ به‌جایش هر ریکوئست یک nonce
تصادفی می‌گیرد که فقط با همان nonce، اسکریپت‌های inline تمپلیت‌های
خودمان اجرا می‌شوند (نه هر اسکریپتی که مثلاً از طریق XSS تزریق شود).
style-src فعلاً همچنان 'unsafe-inline' دارد چون پروژه به‌شدت از
style="..." روی تگ‌ها استفاده می‌کند؛ رفع کامل آن نیاز به یک
refactor جداگانه دارد.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import IS_PRODUCTION
from app.core.csp import generate_nonce, set_nonce


def _build_csp(nonce: str) -> str:
    return (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        nonce = generate_nonce()
        set_nonce(nonce)
        request.state.csp_nonce = nonce

        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = _build_csp(nonce)

        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response