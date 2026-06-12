import asyncio
import logging
import sys
import json
import asyncpg
import redis.asyncio as aioredis

from app.core.config import settings
from app.infrastructure.cache import redis_cache, semantic_cache
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider
from app.infrastructure.embeddings.embedding_service import embedding_service
from app.schemas.chat import ChatMessage
from app.infrastructure.cache.redis_cache import set_showcase_cache, set_exact_cache, normalize_prompt
from app.infrastructure.cache.semantic_cache import set_semantic_cache

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("lerka-precompute")

async def precompute_showcase(showcase: dict, provider: OpenRouterProvider, db_pool: asyncpg.Pool):
    showcase_id = showcase["id"]
    prompt = showcase["prompt"]
    logger.info(f"Starting precomputation for showcase '{showcase_id}'...")
    
    model_responses = {}
    
    # 1. Fetch responses for all showcase free models
    for model_id in settings.SHOWCASE_FREE_MODELS:
        logger.info(f"Querying model {model_id} for showcase '{showcase_id}'...")
        
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant. Answer in the same language as the user."),
            ChatMessage(role="user", content=prompt)
        ]
        
        full_text = []
        try:
            # We enforce 20 RPM throttle by sleeping before/after calls
            await asyncio.sleep(3.5) # ~3.5s sleep ensures we stay below 20 RPM
            
            async for chunk in provider.generate_stream(messages, model_id, temperature=0.7):
                if not chunk.startswith("__USAGE__"):
                    full_text.append(chunk)
                    
            model_responses[model_id] = "".join(full_text)
            logger.info(f"Successfully received response from {model_id}")
            
        except Exception as e:
            logger.error(f"Error querying model {model_id} for showcase '{showcase_id}': {e}")
            model_responses[model_id] = f"[Error fetching response: {e}]"
            
    # 2. Call judge to summarize
    logger.info(f"Generating judge summary for showcase '{showcase_id}' using {settings.JUDGE_MODEL}...")
    judge_prompt = (
        "Combine and summarize the AI model responses below. Be extremely concise, direct, and on-point. "
        "Provide a single unified best answer, and provide a clear text explanation of the reasoning so it's clear how the answer was obtained.\n\n"
    )
    for model_id, resp in model_responses.items():
        judge_prompt += f"--- MODEL: {model_id} ---\n{resp}\n\n"
        
    judge_messages = [
        ChatMessage(role="system", content="You are a helpful synthesis judge assistant. Be extremely concise and on-point."),
        ChatMessage(role="user", content=judge_prompt)
    ]
    
    judge_text = []
    try:
        await asyncio.sleep(3.5)
        async for chunk in provider.generate_stream(judge_messages, settings.JUDGE_MODEL, temperature=0.7):
            if not chunk.startswith("__USAGE__"):
                judge_text.append(chunk)
    except Exception as e:
        logger.error(f"Error generating judge summary: {e}")
        judge_text.append(f"[Error generating summary: {e}]")
        
    judge_summary = "".join(judge_text)
    
    # 3. Create cache payload
    payload = {
        "model_responses": model_responses,
        "judge_summary": judge_summary
    }
    
    # 4. Save to Redis showcase cache (persistent, no TTL)
    await set_showcase_cache(showcase_id, payload)
    
    # Also save to Redis exact cache under the generic compare key format
    await set_exact_cache(prompt, "compare_set", 0.7, 1024, payload)
    
    # 5. Embed the prompt and save to pgvector semantic cache (curated=True)
    norm_prompt = normalize_prompt(prompt)
    logger.info(f"Generating embedding for prompt of showcase '{showcase_id}'...")
    embedding = await embedding_service.get_embedding(norm_prompt)
    
    await set_semantic_cache(embedding, norm_prompt, payload, settings.MODEL_SET_VERSION)
    logger.info(f"Completed precomputation and caching for showcase '{showcase_id}'.\n")

async def main():
    logger.info("Initializing precompute task connections...")
    
    # 1. Connect to Postgres
    postgres_dsn = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    try:
        semantic_cache.db_pool = await asyncpg.create_pool(dsn=postgres_dsn)
        await semantic_cache.init_db(semantic_cache.db_pool)
        logger.info("Connected to Postgres database.")
    except Exception as e:
        logger.critical(f"Failed to connect to Postgres: {e}")
        sys.exit(1)
        
    # 2. Connect to Redis
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
        await redis_cache.cache_redis.ping()
        logger.info("Connected to Redis Cache.")
    except Exception as e:
        logger.critical(f"Failed to connect to Redis: {e}")
        await semantic_cache.db_pool.close()
        sys.exit(1)
        
    # 3. Initialize FastEmbed model
    try:
        embedding_service.initialize()
        logger.info("Warmed up embedding model.")
    except Exception as e:
        logger.critical(f"Failed to initialize embedding model: {e}")
        await redis_cache.cache_redis.close()
        await redis_cache.control_redis.close()
        await semantic_cache.db_pool.close()
        sys.exit(1)
        
    # 4. Perform precomputations
    provider = OpenRouterProvider()
    for showcase in settings.SHOWCASES:
        try:
            await precompute_showcase(showcase, provider, semantic_cache.db_pool)
        except Exception as e:
            logger.error(f"Failed to precompute showcase '{showcase['id']}': {e}")
            
    # 5. Clean up connections
    await redis_cache.cache_redis.close()
    await redis_cache.control_redis.close()
    await semantic_cache.db_pool.close()
    logger.info("Precomputation process finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
