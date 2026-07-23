"""
app/routers/payment.py

Routes for purchasing a subscription plan and handling the Zarinpal
callback after the user returns from the gateway.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import is_valid_csrf
from app.core.limiter import limiter
from app.services.payment_service import (
    start_subscription_purchase,
    finalize_payment,
    PaymentError,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.post("/billing/subscribe/{plan_code}")
@limiter.limit("10/hour")
async def subscribe_to_plan(
    plan_code: str,
    request: Request,
    csrf_token: str = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # این روت با فرم POST معمولی صدا زده می‌شود؛ csrf_token از فرم می‌آید
    form = await request.form()
    submitted_csrf = form.get("csrf_token")

    if not is_valid_csrf(request, submitted_csrf):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "user": user},
            status_code=403,
        )

    try:
        result = await start_subscription_purchase(db, user, plan_code)
    except PaymentError as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": str(e), "user": user},
            status_code=400,
        )

    return RedirectResponse(url=result["payment_url"], status_code=303)


@router.get("/payment/callback")
async def payment_callback(
    request: Request,
    payment_id: int,
    Authority: str = None,
    Status: str = None,
    db: Session = Depends(get_db),
):
    """
    زرین‌پال کاربر را با کوئری‌پارامترهای Authority و Status
    (OK یا NOK) به این آدرس برمی‌گرداند.
    """

    user = get_current_user(request, db)

    if Status != "OK" or not Authority:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "پرداخت توسط شما لغو شد یا ناموفق بود.", "user": user},
            status_code=400,
        )

    try:
        payment = await finalize_payment(db, payment_id, Authority)
    except PaymentError as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": f"تایید پرداخت ناموفق بود: {e}", "user": user},
            status_code=400,
        )

    return templates.TemplateResponse(
        request,
        "payment_success.html",
        {
            "request": request,
            "user": user,
            "payment": payment,
        }
    )