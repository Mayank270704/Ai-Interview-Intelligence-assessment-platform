from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import router as auth_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.resumes import router as resumes_router
from app.core.config import APP_NAME, CORS_ALLOW_ORIGINS

app = FastAPI(title=APP_NAME, version="0.1.0")
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
    return JSONResponse(status_code=503, content={"detail": "Database is unavailable"})
