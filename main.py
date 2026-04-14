from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.router import api_router
from app.infrastructure.database import connect_to_mongo, close_mongo_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

def create_app() -> FastAPI:
    is_prod = settings.ENVIRONMENT.lower() == "production"
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if not is_prod else None,
        docs_url="/docs" if not is_prod else None,
        redoc_url="/redoc" if not is_prod else None,
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)