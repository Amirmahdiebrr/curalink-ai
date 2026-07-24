"""
app/routers/reviews.py

ثبت نظر توسط کاربران واقعی؛ فقط کاربر لاگین‌شده می‌تواند نظر ثبت کند.
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import is_valid_csrf
from app.core.limiter import limiter
from app.services.review_service import create_review


router = APIRouter()


@router.post("/reviews")
@limiter.limit("5/day")
async def submit_review(
    request: Request,
    rating: int = Form(...),
    comment: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/#testimonials", status_code=303)

    comment = (comment or "").strip()

    if comment and 1 <= rating <= 5:
        create_review(db, user.id, rating, comment)

    return RedirectResponse(url="/#testimonials", status_code=303)