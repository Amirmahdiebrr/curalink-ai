"""
app/routers/org_referrals.py

پنل حساب و تراکنش معرفی‌شدگان (برای محاسبه‌ی بونوس دعوت به
آزمایشگاه‌ها/کلینیک‌ها/بیمارستان‌ها).

نکته‌ی امنیتی مهم: این اطلاعات (لیست بیماران معرفی‌شده، مبلغ
تراکنش‌ها و جمع ماهانه) فقط باید در اختیار platform_admin باشد.
خودِ سازمان (org_admin) به این صفحات دسترسی ندارد؛ اگر بخواهیم در
آینده به خودِ سازمان هم نمایش محدودی بدهیم، باید یک صفحه‌ی جداگانه
و کاملاً کنترل‌شده طراحی شود، نه استفاده مجدد از این پنل ادمین.

مسیرها:
- /admin/referrals            : فهرست همه‌ی سازمان‌ها با خلاصه‌ی آماری
- /admin/referrals/{org_id}   : جزئیات کامل معرفی‌شدگان و تراکنش‌های یک سازمان خاص
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, User
from app.services.referral_service import get_all_organizations_summary, get_referral_summary


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _require_platform_admin(request: Request, db: Session):
    user = get_current_user(request, db)

    if not user or user.role != ROLE_PLATFORM_ADMIN:
        return None

    return user


@router.get("/admin/referrals")
async def admin_referrals_list(request: Request, db: Session = Depends(get_db)):

    admin_user = _require_platform_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    summaries = get_all_organizations_summary(db)

    total_paid_all = sum(item["total_paid"] for item in summaries)
    total_referred_all = sum(item["referred_count"] for item in summaries)

    return templates.TemplateResponse(
        request,
        "admin_referrals_list.html",
        {
            "request": request,
            "user": admin_user,
            "summaries": summaries,
            "total_paid_all": total_paid_all,
            "total_referred_all": total_referred_all,
        }
    )


@router.get("/admin/referrals/{org_id}")
async def admin_referrals_detail(org_id: int, request: Request, db: Session = Depends(get_db)):

    admin_user = _require_platform_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    org = (
        db.query(User)
        .filter(User.id == org_id, User.role == ROLE_ORG_ADMIN)
        .first()
    )

    if not org:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این سازمان پیدا نشد.", "user": admin_user},
            status_code=404,
        )

    summary = get_referral_summary(db, org.id)

    return templates.TemplateResponse(
        request,
        "admin_referral_detail.html",
        {
            "request": request,
            "user": admin_user,
            "org": org,
            **summary,
        }
    )