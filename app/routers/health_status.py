# app/routers/health_status.py
"""
app/routers/health_status.py

صفحه‌ی مستقل «وضعیت سلامت من»: امتیاز سلامت، آمار کلی، اقدامات
سریع، یادآوری‌ها، مسیر مراقبت و جدول زمانی سلامت. این محتوا قبلاً
داخل صفحه‌ی اصلی (index.html) بود و اکنون به یک مسیر مجزا منتقل
شده و فقط از طریق نوبار در دسترس است.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token
from app.services.family_service import get_family_members
from app.services.history_service import get_due_followups


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/health-status")
async def health_status_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    csrf_token = get_or_create_csrf_token(request)
    family_members = get_family_members(db, user.id)
    due_followups = get_due_followups(db, user.id)

    return templates.TemplateResponse(
        request,
        "health_status.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "family_members": family_members,
            "due_followups": due_followups,
        }
    )