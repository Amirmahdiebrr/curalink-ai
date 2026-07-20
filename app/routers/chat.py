"""
app/routers/chat.py

Endpoint for the medical Q&A chat attached to a result page
(either a fresh job result, or a saved history record).
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.job_store import get_job
from app.services.history_service import get_record_for_user
from app.services.chat_service import ChatService
from app.services.deepseek import DeepSeekError


router = APIRouter()

chat_service = ChatService()


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    job_id: str | None = None
    record_id: int | None = None
    question: str
    history: list[ChatTurn] = []


@router.post("/chat")
async def chat(request: Request, payload: ChatRequest, db: Session = Depends(get_db)):

    question = (payload.question or "").strip()

    if not question:
        return JSONResponse({"error": "سوال خالی است."}, status_code=400)

    if len(question) > 1000:
        return JSONResponse({"error": "سوال بیش از حد طولانی است."}, status_code=400)

    report_context = None

    if payload.job_id:
        job = get_job(payload.job_id)

        if not job or job.get("status") != "done" or not job.get("result"):
            return JSONResponse({"error": "گزارش مرتبط پیدا نشد."}, status_code=404)

        result = job["result"]
        report_context = (result.get("analysis") or "") + "\n\n" + (result.get("ocr") or "")

    elif payload.record_id:
        user = get_current_user(request, db)

        if not user:
            return JSONResponse({"error": "برای این بخش باید وارد حساب کاربری شوید."}, status_code=401)

        record = get_record_for_user(db, payload.record_id, user.id)

        if not record:
            return JSONResponse({"error": "گزارش مرتبط پیدا نشد."}, status_code=404)

        report_context = (record.analysis_text or "") + "\n\n" + (record.ocr_text or "")

    else:
        return JSONResponse({"error": "شناسه‌ی گزارش ارسال نشده است."}, status_code=400)

    history_data = [turn.model_dump() for turn in payload.history]

    try:
        answer = await chat_service.ask(report_context, history_data, question)
    except DeepSeekError:
        return JSONResponse(
            {"error": "اتصال به سرویس هوش مصنوعی برقرار نشد. لطفاً از فعال بودن اتصال (VPN) سرور مطمئن شوید و دوباره تلاش کنید."},
            status_code=503
        )
    except Exception as e:
        print(f"[Chat] Unexpected error: {e}", flush=True)
        return JSONResponse({"error": "پاسخ‌گویی با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status_code=500)

    return JSONResponse({"answer": answer})