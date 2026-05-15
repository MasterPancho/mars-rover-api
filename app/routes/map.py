from fastapi import APIRouter, HTTPException, Request
from .. import storage
from ..models import MapUpdate
from ..auth import AUTH
from ..limiter import limiter

MAX_MAP_DIM = 100

router = APIRouter()


@router.get("/map", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_map(request: Request):
    return {"width": storage.map_data["width"], "height": storage.map_data["height"], "mines": list(storage.mines.values())}


@router.put("/map", dependencies=[AUTH])
@limiter.limit("10/minute")
def update_map(request: Request, data: MapUpdate):
    if not (1 <= data.width <= MAX_MAP_DIM) or not (1 <= data.height <= MAX_MAP_DIM):
        raise HTTPException(status_code=400, detail=f"Dimensions must be between 1 and {MAX_MAP_DIM}")
    storage.map_data["width"] = data.width
    storage.map_data["height"] = data.height
    return storage.map_data
