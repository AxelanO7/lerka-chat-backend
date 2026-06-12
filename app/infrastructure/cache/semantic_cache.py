import json
import logging
from typing import Optional, Any, Dict, List
import asyncpg
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global database pool to be initialized at startup in main.py
db_pool: Optional[asyncpg.Pool] = None

async def init_db(pool: asyncpg.Pool) -> None:
    """
    Ensures pgvector extension and the semantic_cache table with HNSW index exist.
    """
    async with pool.acquire() as conn:
        # Enable vector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create semantic_cache table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_cache (
                id SERIAL PRIMARY KEY,
                embedding vector(384) NOT NULL,
                normalized_prompt TEXT NOT NULL,
                payload JSONB NOT NULL,
                model_set_version TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Create HNSW index for cosine distance
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS semantic_cache_hnsw_idx 
                ON semantic_cache USING hnsw (embedding vector_cosine_ops);
            """)
        except Exception as e:
            logger.warning(f"Could not create HNSW index (possibly unsupported pgvector version), falling back to ivfflat or default: {e}")

async def get_semantic_cache(embedding: List[float]) -> Optional[Dict[str, Any]]:
    """
    Performs cosine similarity lookup. Similarity = 1 - (embedding <=> query_vector)
    """
    if db_pool is None:
        logger.warning("Postgres pool is not initialized")
        return None
    
    # Cosine distance limit corresponding to similarity >= 0.93: distance <= 0.07
    max_distance = 1.0 - settings.SEMANTIC_SIMILARITY_THRESHOLD
    vector_str = f"[{','.join(map(str, embedding))}]"
    
    query = """
        SELECT payload, 1 - (embedding <=> $1::vector) as similarity
        FROM semantic_cache
        WHERE model_set_version = $2
          AND (embedding <=> $1::vector) <= $3
        ORDER BY embedding <=> $1::vector
        LIMIT 1
    """
    
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, vector_str, settings.MODEL_SET_VERSION, max_distance)
            if row:
                logger.info(f"Semantic cache hit with similarity: {row['similarity']:.4f}")
                return json.loads(row["payload"])
    except Exception as e:
        logger.error(f"Error querying semantic cache: {e}")
    
    return None

async def set_semantic_cache(
    embedding: List[float], 
    normalized_prompt: str, 
    payload: Dict[str, Any], 
    model_set_version: str
) -> None:
    """
    Saves a result to the semantic cache table.
    """
    if db_pool is None:
        logger.warning("Postgres pool is not initialized")
        return
    
    vector_str = f"[{','.join(map(str, embedding))}]"
    query = """
        INSERT INTO semantic_cache (embedding, normalized_prompt, payload, model_set_version)
        VALUES ($1::vector, $2, $3, $4)
    """
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                query, 
                vector_str, 
                normalized_prompt, 
                json.dumps(payload), 
                model_set_version
            )
            logger.info("Semantic cache written successfully.")
    except Exception as e:
        logger.error(f"Error writing to semantic cache: {e}")
