"""
app/core/language.py

Minimal, request-scoped i18n infrastructure:
- reads the language cookie once per request (LanguageMiddleware)
- exposes t(key) / get_lang() / lang_dir() usable anywhere, including
  inside Jinja templates (registered as globals in app/core/templating.py)
"""

from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.i18n.fa import FA_TRANSLATIONS
from app.i18n.en import EN_TRANSLATIONS

SUPPORTED_LANGS = ["fa", "en"]
DEFAULT_LANG = "fa"
LANG_COOKIE_NAME = "cl_lang"
LANG_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

TRANSLATIONS = {
    "fa": FA_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}

_current_lang: ContextVar[str] = ContextVar("current_lang", default=DEFAULT_LANG)


def normalize_lang(value: str | None) -> str:
    if value in SUPPORTED_LANGS:
        return value
    return DEFAULT_LANG


def get_lang() -> str:
    return _current_lang.get()


def set_lang(lang: str) -> None:
    _current_lang.set(normalize_lang(lang))


def t(key: str, **kwargs) -> str:
    """
    Translate `key` into the current request's language. Falls back to
    the Persian table (and finally to the raw key) if missing.
    """
    lang = get_lang()
    table = TRANSLATIONS.get(lang, FA_TRANSLATIONS)
    text = table.get(key)

    if text is None:
        text = FA_TRANSLATIONS.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text

    return text


def lang_dir(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "ltr" if lang == "en" else "rtl"


class LanguageMiddleware(BaseHTTPMiddleware):
    """
    Reads the cl_lang cookie once per request and makes it available
    through get_lang()/t()/lang_dir() for the rest of the request,
    including inside Jinja templates rendered during that request.
    """

    async def dispatch(self, request: Request, call_next):
        cookie_lang = request.cookies.get(LANG_COOKIE_NAME)
        set_lang(normalize_lang(cookie_lang))
        request.state.lang = get_lang()

        response: Response = await call_next(request)
        return response