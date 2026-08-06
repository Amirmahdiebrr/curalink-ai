"""
app/core/jdate.py

Lightweight Gregorian <-> Jalali (Persian) calendar conversion, no
external dependencies. Dates render in Jalali when the site language
is Persian, and in Gregorian when it's English.
"""

from datetime import date, datetime

from app.core.language import get_lang

_G_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_J_DAYS_IN_MONTH = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def _is_leap_gregorian(gy: int) -> bool:
    return (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400

    for i in range(gm2):
        g_day_no += _G_DAYS_IN_MONTH[i]

    if gm2 > 1 and _is_leap_gregorian(gy):
        g_day_no += 1

    g_day_no += gd2

    j_day_no = g_day_no - 79

    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    jm = 12
    jd = j_day_no + 1

    for i in range(11):
        if j_day_no < _J_DAYS_IN_MONTH[i]:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= _J_DAYS_IN_MONTH[i]

    return jy, jm, jd


def to_persian_digits(value: str) -> str:
    return "".join(_PERSIAN_DIGITS[int(ch)] if ch.isdigit() else ch for ch in value)


def jdate(value, fmt: str = "%Y/%m/%d", lang: str | None = None) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        value = value.date()
    elif not isinstance(value, date):
        return str(value)

    lang = lang or get_lang()

    if lang == "en":
        return value.strftime(fmt.replace("/", "-"))

    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    formatted = (
        fmt.replace("%Y", f"{jy:04d}")
        .replace("%m", f"{jm:02d}")
        .replace("%d", f"{jd:02d}")
    )
    return to_persian_digits(formatted)


def jdatetime(value, lang: str | None = None) -> str:
    if value is None:
        return ""

    date_part = jdate(value, lang=lang)

    if isinstance(value, datetime):
        time_part = value.strftime("%H:%M")
        lang = lang or get_lang()
        if lang != "en":
            time_part = to_persian_digits(time_part)
        return f"{date_part} {time_part}"

    return date_part