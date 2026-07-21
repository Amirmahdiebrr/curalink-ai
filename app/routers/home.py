from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "user": user, "csrf_token": csrf_token}
    )