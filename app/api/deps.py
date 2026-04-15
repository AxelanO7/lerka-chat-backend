from fastapi import Header, HTTPException, status
from app.core.config import settings

def verify_internal_gateway(x_internal_secret: str = Header(...)):
    if x_internal_secret != settings.INTERNAL_GATEWAY_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal gateway secret")
    return True