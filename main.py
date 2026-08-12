# main.py
import app.core.templating  # noqa: F401 - patches Jinja2Templates with i18n globals

from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

logger.info("=" * 50)
logger.info("RUNNING MAIN.PY")
logger.info("=" * 50)

import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import SESSION_SECRET_KEY, IS_PRODUCTION
from app.database import init_db, SessionLocal
from app.core.limiter import limiter
from app.core.language import LanguageMiddleware

from app.routers.home import router as home_router
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router
from app.routers.history import router as history_router
from app.routers.trends import router as trends_router
from app.routers.chat import router as chat_router
from app.routers.family import router as family_router
from app.routers.diet import router as diet_router
from app.routers.visit_prep import router as visit_prep_router
from app.routers.workout import router as workout_router
from app.routers.doctor_review import router as doctor_review_router
from app.routers.prescription_public import router as prescription_public_router
from app.routers.reviews import router as reviews_router
from app.routers.health_status import router as health_status_router
from app.routers.language import router as language_router
from app.routers.org_referrals import router as org_referrals_router
from app.routers.admin import router as admin_router
from app.routers.payment import router as payment_router
from app.routers.education import router as education_router

from app.services.job_store import purge_old_jobs
from app.services import pending_action_store
from app.services.reminder_service import ReminderService

JOB_CLEANUP_INTERVAL_SECONDS = 60 * 30
REMINDER_CHECK_INTERVAL_SECONDS = 60 * 60 * 24


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
    max_age=60 * 60 * 24 * 14,
)

app.add_middleware(LanguageMiddleware)

init_db()

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# ==========================
# Routers
# ==========================

app.include_router(home_router)
app.include_router(analyze_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(trends_router)
app.include_router(chat_router)
app.include_router(family_router)
app.include_router(diet_router)
app.include_router(visit_prep_router)
app.include_router(workout_router)
app.include_router(doctor_review_router)
app.include_router(prescription_public_router)
app.include_router(admin_router)
app.include_router(payment_router)
app.include_router(reviews_router)
app.include_router(health_status_router)
app.include_router(language_router)
app.include_router(org_referrals_router)
app.include_router(education_router)


# ==========================
# Background tasks
# ==========================

async def _job_cleanup_loop():
    while True:
        await asyncio.sleep(JOB_CLEANUP_INTERVAL_SECONDS)
        try:
            purge_old_jobs()
        except Exception as e:
            logger.error(f"[JobStore] Cleanup loop error: {e}")
        try:
            pending_action_store.purge_old()
        except Exception as e:
            logger.error(f"[PendingActionStore] Cleanup loop error: {e}")


async def _reminder_check_loop():
    while True:
        db = SessionLocal()
        try:
            await ReminderService().run(db)
        except Exception as e:
            logger.error(f"[ReminderService] Check loop error: {e}")
        finally:
            db.close()
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_job_cleanup_task():
    asyncio.create_task(_job_cleanup_loop())


@app.on_event("startup")
async def start_reminder_check_task():
    asyncio.create_task(_reminder_check_loop())


@app.get("/healthz")
async def health_check():
    return {"status": "ok"}


logger.info("Application configured. Routes registered: %d", len(app.routes))