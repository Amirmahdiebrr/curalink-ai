"""
app/core/csrf.py

Lightweight session-based CSRF token generation and validation.
"""

import secrets

from fastapi import Request


CSRF_SESSION_KEY = "csrf_token"


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)

    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token

    return token


def is_valid_csrf(request: Request, token: str | None) -> bool:
    if not token:
        return False

    session_token = request.session.get(CSRF_SESSION_KEY)

    if not session_token:
        return False

    return secrets.compare_digest(session_token, token)