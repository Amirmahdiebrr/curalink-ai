"""
app/routers/education.py
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import ROLE_PLATFORM_ADMIN


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/education")
async def education_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "education.html",
        {"request": request, "user": user}
    )


@router.get("/education/course/{course_id}")
async def education_course_page(course_id: int, request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "education_course.html",
        {"request": request, "user": user, "course_id": course_id}
    )


@router.get("/admin/analytics")
async def analytics_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user or user.role != ROLE_PLATFORM_ADMIN:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request,
        "analytics.html",
        {"request": request, "user": user}
    )