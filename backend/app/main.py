from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import APP_NAME

app = FastAPI(title=APP_NAME, version="0.1.0")
app.include_router(health_router, prefix="/api/v1")

