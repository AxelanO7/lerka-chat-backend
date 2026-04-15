from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.api.deps import verify_internal_gateway

router = APIRouter()

@router.post("/stream", dependencies=[Depends(verify_internal_gateway)])
async def chat_stream(request: ChatRequest):
    chat_service = ChatService()
    generator = chat_service.stream_chat(
        messages=request.messages,
        model_id=request.model_id,
        temperature=request.temperature
    )
    return StreamingResponse(generator, media_type="text/plain")