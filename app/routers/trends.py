"""
app/routers/trends.py

Shows latest lab values and historical trend charts for a logged-in user.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.history_service import (
    get_latest_results_by_test,
    get_test_history,
    get_distinct_test_names,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/trends")
async def trends_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    latest_results = get_latest_results_by_test(db, user.id)
    test_names = get_distinct_test_names(db, user.id)

    return templates.TemplateResponse(
        request,
        "trends.html",
        {
            "request": request,
            "user": user,
            "latest_results": latest_results,
            "test_names": test_names,
        }
    )


@router.get("/trends/data/{test_name}")
async def trends_data(request: Request, test_name: str, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    history = get_test_history(db, user.id, test_name)

    points = [
        {
            "date": item.test_date.strftime("%Y-%m-%d"),
            "value": item.value_numeric,
            "unit": item.unit,
            "status": item.status,
        }
        for item in history
    ]

    return JSONResponse({"test_name": test_name, "points": points})