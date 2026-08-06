"""
app/routers/org_referrals.py

صفحه‌ی حساب و تراکنش معرفی‌شدگان برای آزمایشگاه/کلینیک/بیمارستان:
لیست بیمارانی که با معرفی این سازمان ثبت‌نام کرده‌اند، تراکنش‌های
موفق آن‌ها، و مجموع پرداختی ماهانه برای محاسبه‌ی بونوس دعوت.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN
from app.services.referral_service import get_referral_summary


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/org/referrals")
async def org_referrals_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if user.role not in (ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN):
        return RedirectResponse(url="/", status_code=303)

    summary = get_referral_summary(db, user.id)

    return templates.TemplateResponse(
        request,
        "org_referrals.html",
        {
            "request": request,
            "user": user,
            **summary,
        }
    )