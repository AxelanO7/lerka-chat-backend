import asyncio
import logging
import sys
import httpx
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncpg
import redis.asyncio as aioredis

from app.core.config import settings
from app.api.router import api_router
from app.infrastructure.cache import redis_cache, semantic_cache
from app.infrastructure.embeddings.embedding_service import embedding_service

# Configure structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def fetch_and_cache_prices(redis_client: aioredis.Redis):
    """
    Fetches the price table from OpenRouter and caches it in Redis.
    """
    url = "https://openrouter.ai/api/v1/models"
    logger.info(f"Fetching OpenRouter price table from {url}...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                price_table = {}
                for model in data.get("data", []):
                    model_id = model.get("id")
                    pricing = model.get("pricing", {})
                    # OpenRouter rates are usually USD per 1 token (or float format)
                    try:
                        prompt = float(pricing.get("prompt", 0.0))
                        completion = float(pricing.get("completion", 0.0))
                        price_table[model_id] = {
                            "prompt": prompt,
                            "completion": completion
                        }
                    except (ValueError, TypeError):
                        continue
                
                if price_table:
                    # Save entire table as JSON
                    await redis_client.set("price_table", json.dumps(price_table))
                    logger.info(f"Price table successfully cached in Redis. Total models: {len(price_table)}")
                    return
            logger.error(f"Failed to fetch prices from OpenRouter, status code: {resp.status_code}")
    except Exception as e:
        logger.error(f"Error fetching OpenRouter prices: {e}")
    
    # Fallback default prices if OpenRouter is unreachable
    logger.warning("Using fallback default prices...")
    fallbacks = {
        "openai/gpt-oss-20b": {"prompt": 0.000000075, "completion": 0.000000075},
        "google/gemma-4-26b-a4b-it": {"prompt": 0.00000008, "completion": 0.00000008},
        "anthropic/claude-3-haiku": {"prompt": 0.00000025, "completion": 0.00000125}
    }
    try:
        await redis_client.set("price_table", json.dumps(fallbacks))
    except Exception as e:
        logger.error(f"Failed to save fallback price table to Redis: {e}")

async def price_refresh_loop(redis_client: aioredis.Redis):
    """
    Background task to refresh prices every 24 hours.
    """
    while True:
        await asyncio.sleep(24 * 3600)
        await fetch_and_cache_prices(redis_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. DEV_MODE Boot Assertion
    if settings.DEV_MODE:
        logger.critical("FATAL: DEV_MODE is enabled (true). FastAPI Chat Backend refusing to boot for safety.")
        sys.exit("Refusing to boot: DEV_MODE=true")

    logger.info("Initializing resources on startup...")

    # 2. Initialize Postgres Connection Pool
    postgres_dsn = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    try:
        semantic_cache.db_pool = await asyncpg.create_pool(
            dsn=postgres_dsn,
            min_size=2,
            max_size=10
        )
        logger.info("Postgres pool successfully initialized.")
        # Setup tables and HNSW index
        await semantic_cache.init_db(semantic_cache.db_pool)
    except Exception as e:
        logger.critical(f"Failed to initialize Postgres pool: {e}")
        sys.exit(1)

    # 3. Initialize Redis Cache and Control Clients
    try:
        redis_cache.cache_redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB_CACHE,
            decode_responses=True
        )
        redis_cache.control_redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB_CONTROL,
            decode_responses=True
        )
        # Verify connection
        await redis_cache.cache_redis.ping()
        await redis_cache.control_redis.ping()
        logger.info("Redis clients successfully initialized.")
    except Exception as e:
        logger.critical(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    # 4. Warm up fastembed model
    try:
        logger.info("Warming up FastEmbed embedding model...")
        embedding_service.initialize()
        logger.info("FastEmbed embedding model warmed up.")
    except Exception as e:
        logger.critical(f"Failed to initialize FastEmbed model: {e}")
        sys.exit(1)

    # 5. Fetch and Cache Prices
    await fetch_and_cache_prices(redis_cache.control_redis)
    # Start background price refresh task
    refresh_task = asyncio.create_task(price_refresh_loop(redis_cache.control_redis))

    yield

    # Shutdown
    logger.info("Cleaning up resources on shutdown...")
    refresh_task.cancel()
    
    if semantic_cache.db_pool:
        await semantic_cache.db_pool.close()
        logger.info("Postgres pool closed.")
        
    if redis_cache.cache_redis:
        await redis_cache.cache_redis.close()
        logger.info("Redis Cache client closed.")
        
    if redis_cache.control_redis:
        await redis_cache.control_redis.close()
        logger.info("Redis Control client closed.")

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