import re
import hashlib
import json
import logging
from typing import Optional, Any, Dict
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis instances to be initialized at startup in main.py
cache_redis: Optional[aioredis.Redis] = None
control_redis: Optional[aioredis.Redis] = None

def normalize_prompt(prompt: str) -> str:
    """
    Normalizes a prompt by converting to lowercase, collapsing whitespace,
    and stripping trailing punctuation.
    """
    if not prompt:
        return ""
    p = prompt.lower().strip()
    p = re.sub(r'\s+', ' ', p)
    # Strip trailing punctuation
    p = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?]+$', '', p)
    return p.strip()

def get_cache_key(prompt: str, model_id: str, temperature: float, max_tokens: int) -> str:
    """
    Generates exact match cache key: compare:{sha256(norm_prompt:MODEL_SET_VERSION:params_hash)}
    """
    norm_prompt = normalize_prompt(prompt)
    params_str = f"{temperature}:{max_tokens}:{model_id}"
    params_hash = hashlib.sha256(params_str.encode('utf-8')).hexdigest()
    
    combined = f"{norm_prompt}:{settings.MODEL_SET_VERSION}:{params_hash}"
    combined_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return f"compare:{combined_hash}"

async def get_exact_cache(prompt: str, model_id: str, temperature: float, max_tokens: int) -> Optional[Dict[str, Any]]:
    if cache_redis is None:
        logger.warning("Redis cache client is not initialized")
        return None
    
    key = get_cache_key(prompt, model_id, temperature, max_tokens)
    try:
        val = await cache_redis.get(key)
        if val:
            logger.info(f"Exact cache hit for key: {key}")
            return json.loads(val)
    except Exception as e:
        logger.error(f"Error reading exact cache: {e}")
    return None

async def set_exact_cache(prompt: str, model_id: str, temperature: float, max_tokens: int, payload: Dict[str, Any]) -> None:
    if cache_redis is None:
        logger.warning("Redis cache client is not initialized")
        return
    
    key = get_cache_key(prompt, model_id, temperature, max_tokens)
    ttl = 14 * 86400  # 14 days
    try:
        await cache_redis.setex(key, ttl, json.dumps(payload))
        logger.info(f"Exact cache set for key: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.error(f"Error writing exact cache: {e}")

# Showcase caching helpers
async def get_showcase_cache(showcase_id: str) -> Optional[Dict[str, Any]]:
    if cache_redis is None:
        return None
    key = f"showcase:{showcase_id}"
    try:
        val = await cache_redis.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.error(f"Error reading showcase cache: {e}")
    return None

async def set_showcase_cache(showcase_id: str, payload: Dict[str, Any]) -> None:
    if cache_redis is None:
        return
    key = f"showcase:{showcase_id}"
    try:
        # Showcases are persisted indefinitely or with very long TTL, but since it's a showcase cache
        # we can set a long TTL (e.g. 30 days) or no TTL if volatile-lru does not evict it.
        # Since policy is volatile-lru, keys without TTL are NOT evicted. Showcases MUST not be evicted.
        # So we store showcases with NO TTL to protect them from eviction!
        await cache_redis.set(key, json.dumps(payload))
        logger.info(f"Showcase cache set for key: {key} (No TTL)")
    except Exception as e:
        logger.error(f"Error writing showcase cache: {e}")
