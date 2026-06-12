from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from app.core.config import settings
from app.infrastructure.cache.redis_cache import get_showcase_cache, set_showcase_cache
from app.api.deps import verify_internal_gateway

router = APIRouter()

@router.get("")
async def list_showcases():
    """
    Returns all showcases with their cached precomputed comparison results from Redis.
    """
    results = []
    for showcase in settings.SHOWCASES:
        payload = await get_showcase_cache(showcase["id"])
        results.append({
            "id": showcase["id"],
            "title": showcase["title"],
            "prompt": showcase["prompt"],
            "is_precomputed": payload is not None,
            "data": payload
        })
    return results

@router.get("/{showcase_id}")
async def get_showcase(showcase_id: str):
    """
    Returns a specific showcase's precomputed comparison results.
    """
    payload = await get_showcase_cache(showcase_id)
    if not payload:
        raise HTTPException(
            status_code=404, 
            detail=f"Showcase with ID '{showcase_id}' has not been precomputed yet."
        )
    return payload

@router.post("/{showcase_id}/cache", dependencies=[Depends(verify_internal_gateway)])
async def update_showcase_cache(showcase_id: str, payload: Dict[str, Any]):
    """
    Internal endpoint to update a showcase's cache.
    """
    # Verify showcase_id exists in settings
    valid_ids = [s["id"] for s in settings.SHOWCASES]
    if showcase_id not in valid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid showcase ID. Must be one of: {', '.join(valid_ids)}"
        )
    await set_showcase_cache(showcase_id, payload)
    return {"status": "success", "message": f"Showcase '{showcase_id}' cache updated"}
