"""
app/routers/language.py

Lets the user switch the site language. Sets a long-lived cookie and
redirects back to the page they were on.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.language import normalize_lang, LANG_COOKIE_NAME, LANG_COOKIE_MAX_AGE

router = APIRouter()


@router.get("/set-language/{lang}")
async def set_language(lang: str, request: Request):
    target = normalize_lang(lang)
    referer = request.headers.get("referer") or "/"

    response = RedirectResponse(url=referer, status_code=303)
    response.set_cookie(
        key=LANG_COOKIE_NAME,
        value=target,
        max_age=LANG_COOKIE_MAX_AGE,
        httponly=False,
        samesite="lax",
    )
    return response