"""
app/core/security_headers.py

Middleware که هدرهای امنیتی استاندارد را به تمام پاسخ‌های HTTP اضافه
می‌کند: CSP (کنترل منابع مجاز برای اسکریپت/فونت/تصویر/استایل)،
X-Frame-Options (جلوگیری از clickjacking)، X-Content-Type-Options
(جلوگیری از MIME sniffing) و در حالت production، Strict-Transport-
-Security (اجبار HTTPS).

CSP طوری تنظیم شده که با منابع فعلی پروژه (Google Fonts، cdnjs برای
Chart.js، و اسکریپت‌های inline موجود در تمپلیت‌ها) سازگار باشد.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import IS_PRODUCTION


CSP_DIRECTIVES = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
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
        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = CSP_DIRECTIVES

        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response