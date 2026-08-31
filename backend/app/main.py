from fastapi import FastAPI

from app.api.v1.candidates import router as candidates_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.resumes import router as resumes_router
from app.core.config import APP_NAME

app = FastAPI(title=APP_NAME, version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(candidates_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")
app.include_router(interviews_router, prefix="/api/v1")

