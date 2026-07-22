"""
app/routers/trends.py

Shows latest lab values and historical trend charts for a logged-in user
or one of their family members.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.family_service import get_family_members, get_family_member_for_user
from app.services.history_service import (
    get_latest_results_by_test,
    get_test_history,
    get_distinct_test_names,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _resolve_family_member_id(db: Session, user_id: int, raw_value: str | None) -> int | None:
    if not raw_value or raw_value.strip() == "self":
        return None

    try:
        fm_id = int(raw_value.strip())
    except ValueError:
        return None

    member = get_family_member_for_user(db, fm_id, user_id)
    return member.id if member else None


@router.get("/trends")
async def trends_page(request: Request, family_member_id: str = None, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    resolved_family_member_id = _resolve_family_member_id(db, user.id, family_member_id)

    latest_results = get_latest_results_by_test(db, user.id, resolved_family_member_id)
    test_names = get_distinct_test_names(db, user.id, resolved_family_member_id)

    return templates.TemplateResponse(
        request,
        "trends.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "selected_family_member_id": resolved_family_member_id,
            "latest_results": latest_results,
            "test_names": test_names,
        }
    )


@router.get("/trends/data/{test_name}")
async def trends_data(request: Request, test_name: str, family_member_id: str = None, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    resolved_family_member_id = _resolve_family_member_id(db, user.id, family_member_id)

    history = get_test_history(db, user.id, test_name, resolved_family_member_id)

    points = [
        {
            "date": item.test_date.strftime("%Y-%m-%d"),
            "value": item.value_numeric,
            "unit": item.unit,
            "status": item.status,
            "reference_range": item.reference_range,
        }
        for item in history
    ]

    return JSONResponse({"test_name": test_name, "points": points})