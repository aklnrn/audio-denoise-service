from fastapi import FastAPI

from app.config import get_settings
from app.routes import router

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message": f"{settings.app_name} is running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}