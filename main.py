print("=" * 50)
print("RUNNING MAIN.PY")
print("=" * 50)


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET_KEY
from app.database import init_db

from app.routers.home import router as home_router
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router
from app.routers.history import router as history_router
from app.routers.trends import router as trends_router


app = FastAPI(
    title="CuraLink AI",
    version="1.0.0"
)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

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


print("ROUTES:")
for route in app.routes:
    print(route)