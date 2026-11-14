from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.db import init_db
from backend.app.routers import bookings, ideas, impact, notifications, proiecte, spaces, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Loc Comun API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    parts = [f"{'.'.join(str(p) for p in e['loc'][1:]) or e['loc'][0]}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Date invalide - " + "; ".join(parts)})


for _router in (users, spaces, ideas, bookings, notifications, impact, proiecte):
    app.include_router(_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
