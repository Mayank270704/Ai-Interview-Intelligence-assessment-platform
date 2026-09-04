import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import router as auth_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.resumes import router as resumes_router
from app.core.config import APP_NAME, CORS_ALLOW_ORIGINS, missing_required_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Name the settings this deployment is missing, once, at startup.

    Each one breaks a specific user-facing step (sign-in, resume upload,
    question generation) with an error the caller cannot act on, and finding
    that out one failed request at a time is what makes it hard to diagnose.
    Names only -- no value of any setting is ever logged.
    """
    missing = missing_required_settings()
    if missing:
        logger.error(
            "Missing required configuration: %s. See backend/.env.example; the "
            "features that depend on these settings will fail until they are set.",
            ", ".join(missing),
        )
    yield


app = FastAPI(title=APP_NAME, version="0.1.0", lifespan=lifespan)
# Bearer tokens (not cookies) carry auth, so credentials stay disabled and the
# origin allowlist is explicit rather than a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(candidates_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")


@app.exception_handler(SQLAlchemyError)
def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error while handling %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "Database is unavailable"})
