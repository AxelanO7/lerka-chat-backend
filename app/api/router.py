from fastapi import APIRouter
from app.api.routes import chat, showcase, documents

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(showcase.router, prefix="/showcase", tags=["showcase"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])