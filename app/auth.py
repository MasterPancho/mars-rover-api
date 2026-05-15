import os
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str = Depends(_api_key_header)):
    api_key = os.getenv("API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server API key not configured")
    if key != api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

AUTH = Depends(require_api_key)
