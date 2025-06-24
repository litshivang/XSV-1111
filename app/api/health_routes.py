from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("/ping", tags=["health"])
def ping():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version
    }
