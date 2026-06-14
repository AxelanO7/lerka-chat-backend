from app.infrastructure.cache.semantic_cache import db_pool
from app.infrastructure.embeddings.embedding_service import embedding_service
from typing import List

async def retrieve(query: str, user_id: str, session_id: str = None, k: int = 4) -> List[str]:
    vector = await embedding_service.get_embedding(query)
    
    # Cosine distance operator is <=> in pgvector
    sql = """
        SELECT chunk_text 
        FROM document_chunks 
        WHERE user_id = $1 AND kb_scope = 'personal'
        ORDER BY embedding <=> $2
        LIMIT $3
    """
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(sql, user_id, vector, k)
        return [r["chunk_text"] for r in rows]
