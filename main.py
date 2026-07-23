print("=" * 50)
print("RUNNING MAIN.PY")
print("=" * 50)

import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import SESSION_SECRET_KEY, APP_BASE_URL, IS_PRODUCTION
from app.database import init_db, SessionLocal
from app.core.limiter import limiter

from app.routers.home import router as home_router
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router
from app.routers.history import router as history_router
from app.routers.trends import router as trends_router
from app.routers.chat import router as chat_router
from app.routers.family import router as family_router
from app.routers.diet import router as diet_router
from app.routers.visit_prep import router as visit_prep_router

from app.services.job_store import purge_old_jobs
from app.services import pending_action_store
from app.services.reminder_service import ReminderService
from app.routers.admin import router as admin_router

from app.routers.payment import router as payment_router

JOB_CLEANUP_INTERVAL_SECONDS = 60 * 30  # هر ۳۰ دقیقه
REMINDER_CHECK_INTERVAL_SECONDS = 60 * 60 * 24  # هر ۲۴ ساعت


app = FastAPI(
    title="CuraLink AI",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    https_only=IS_PRODUCTION,
    same_site="lax",
    max_age=60 * 60 * 24 * 14,  # ۱۴ روز
)

init_db()

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.include_router(home_router)
app.include_router(analyze_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(trends_router)
app.include_router(chat_router)
app.include_router(family_router)
app.include_router(diet_router)
app.include_router(visit_prep_router)
app.include_router(admin_router)
app.include_router(payment_router)


async def _job_cleanup_loop():
    while True:
        await asyncio.sleep(JOB_CLEANUP_INTERVAL_SECONDS)
        try:
            purge_old_jobs()
        except Exception as e:
            print(f"[JobStore] Cleanup loop error: {e}", flush=True)
        try:
            pending_action_store.purge_old()
        except Exception as e:
            print(f"[PendingActionStore] Cleanup loop error: {e}", flush=True)


async def _reminder_check_loop():
    while True:
        db = SessionLocal()
        try:
            await ReminderService().run(db)
        except Exception as e:
            print(f"[ReminderService] Check loop error: {e}", flush=True)
        finally:
            db.close()
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_job_cleanup_task():
    asyncio.create_task(_job_cleanup_loop())


@app.on_event("startup")
async def start_reminder_check_task():
    asyncio.create_task(_reminder_check_loop())


print("ROUTES:")
for route in app.routes:
    print(route)