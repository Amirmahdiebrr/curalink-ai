"""
app/routers/series.py

اندپوینت کمکی برای پر کردن لیست «سری‌های آزمایش قبلی» یک کاربر (یا
یکی از اعضای خانواده‌اش) در فرم آپلود، وقتی کاربر گزینه‌ی «ادامه‌ی
یک سری موجود» را انتخاب می‌کند.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.family_service import get_family_member_for_user
from app.services.history_service import get_user_series_options
from app.core.exam_types import EXAM_TYPE_LABELS


router = APIRouter()


def _resolve_family_member_id(db: Session, user_id: int, raw_value: str | None):
    if not raw_value or raw_value.strip() == "" or raw_value.strip() == "self":
        return None

    try:
        fm_id = int(raw_value.strip())
    except ValueError:
        return None

    member = get_family_member_for_user(db, fm_id, user_id)

    return member.id if member else None


@router.get("/series/options")
async def series_options(request: Request, family_member_id: str = None, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    resolved_family_member_id = _resolve_family_member_id(db, user.id, family_member_id)

    options = get_user_series_options(db, user.id, resolved_family_member_id)

    return JSONResponse({
        "options": [
            {
                "series_id": o["series_id"],
                "label": (
                    f"{EXAM_TYPE_LABELS.get(o['exam_type'], o['exam_type'] or 'نامشخص')} — "
                    f"{o['count']} آزمایش ثبت‌شده — آخرین: {o['last_date'].strftime('%Y-%m-%d')}"
                ),
            }
            for o in options
        ]
    })