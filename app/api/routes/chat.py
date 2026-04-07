from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import logging

from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.api.deps import get_chat_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("")
async def create_chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    async def event_generator():
        try:
            async for chunk in chat_service.process_chat_stream(request):
                yield f"data: {chunk}  "
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: [ERROR] {str(e)}  "
        finally:
            yield "data: [DONE]  "

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    ) 