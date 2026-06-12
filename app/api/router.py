from fastapi import APIRouter
from app.api.routes import chat, showcase

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(showcase.router, prefix="/showcase", tags=["showcase"])