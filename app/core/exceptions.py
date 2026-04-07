from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class ChatServiceException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

async def chat_service_exception_handler(request: Request, exc: ChatServiceException):
    logger.warning(f"Chat service exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
