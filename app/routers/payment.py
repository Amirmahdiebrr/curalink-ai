"""
app/routers/payment.py

خرید اشتراک، پرداخت pay-per-use (از طریق سایر روترها آغاز می‌شود)، و
هندل کردن callback زرین‌پال برای هر دو نوع پرداخت.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import is_valid_csrf
from app.core.limiter import limiter
from app.models import PURPOSE_SUBSCRIPTION, PURPOSE_EXAM_ANALYSIS, PURPOSE_DIET_PLAN, PURPOSE_VISIT_PREP
from app.services import pending_action_store
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
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

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

    if payment.purpose == PURPOSE_SUBSCRIPTION:
        return templates.TemplateResponse(
            request,
            "payment_success.html",
            {"request": request, "user": user, "payment": payment}
        )

    action = pending_action_store.get(payment.id)

    if not action or action.get("error"):
        error_text = (action.get("error") if action else None) or (
            "پرداخت با موفقیت انجام شد اما در پردازش درخواست خطایی رخ داد. لطفاً با پشتیبانی تماس بگیرید."
        )
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": error_text, "user": user},
            status_code=500,
        )

    result_type = action.get("result_type")
    result_id = action.get("result_id")

    pending_action_store.delete(payment.id)

    if payment.purpose == PURPOSE_EXAM_ANALYSIS and result_type == "job":
        return RedirectResponse(url=f"/processing/{result_id}", status_code=303)

    if payment.purpose == PURPOSE_DIET_PLAN and result_type == "diet_record":
        return RedirectResponse(url=f"/diet/history/{result_id}", status_code=303)

    if payment.purpose == PURPOSE_VISIT_PREP and result_type == "visit_prep_record":
        return RedirectResponse(url=f"/visit-prep/history/{result_id}", status_code=303)

    return templates.TemplateResponse(
        request,
        "error.html",
        {"request": request, "message": "پرداخت انجام شد اما نتیجه‌ی درخواست یافت نشد.", "user": user},
        status_code=500,
    )