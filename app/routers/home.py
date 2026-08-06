from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token
from app.services.family_service import get_family_members
from app.services.history_service import get_due_followups
from app.services.review_service import get_latest_reviews


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    csrf_token = get_or_create_csrf_token(request)

    family_members = []
    due_followups = []

    if user:
        family_members = get_family_members(db, user.id)
        due_followups = get_due_followups(db, user.id)

    reviews = get_latest_reviews(db, limit=6)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "family_members": family_members,
            "due_followups": due_followups,
            "reviews": reviews,
            "now": datetime.utcnow(),
        }
    )