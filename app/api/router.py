from fastapi import APIRouter
from app.api.routes import chat, budget

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(budget.router, prefix="/budget", tags=["budget"]) 