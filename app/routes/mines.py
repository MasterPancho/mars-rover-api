from fastapi import APIRouter, HTTPException, Request
from .. import storage
from ..models import MineCreate, MineUpdate
from ..auth import AUTH
from ..limiter import limiter

MAX_MINES = 50

router = APIRouter()


@router.get("/mines", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_mines(request: Request):
    return list(storage.mines.values())


@router.get("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_mine(request: Request, mine_id: int):
    if mine_id not in storage.mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    return storage.mines[mine_id]


@router.post("/mines", dependencies=[AUTH])
@limiter.limit("30/minute")
def create_mine(request: Request, mine: MineCreate):
    if len(storage.mines) >= MAX_MINES:
        raise HTTPException(status_code=400, detail=f"Mine limit reached ({MAX_MINES} max)")
    if mine.x < 0 or mine.y < 0 or mine.x >= storage.map_data["width"] or mine.y >= storage.map_data["height"]:
        raise HTTPException(status_code=400, detail="Coordinates out of map bounds")
    new_mine = {"id": storage.mine_id_counter, "x": mine.x, "y": mine.y, "serial_number": mine.serial_number}
    storage.mines[storage.mine_id_counter] = new_mine
    storage.mine_id_counter += 1
    return {"id": new_mine["id"]}


@router.put("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("20/minute")
def update_mine(request: Request, mine_id: int, mine_update: MineUpdate):
    if mine_id not in storage.mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    mine = storage.mines[mine_id]
    if mine_update.x is not None:
        if mine_update.x < 0 or mine_update.x >= storage.map_data["width"]:
            raise HTTPException(status_code=400, detail="Invalid X coordinate")
        mine["x"] = mine_update.x
    if mine_update.y is not None:
        if mine_update.y < 0 or mine_update.y >= storage.map_data["height"]:
            raise HTTPException(status_code=400, detail="Invalid Y coordinate")
        mine["y"] = mine_update.y
    if mine_update.serial_number is not None:
        mine["serial_number"] = mine_update.serial_number
    return mine


@router.delete("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("30/minute")
def delete_mine(request: Request, mine_id: int):
    if mine_id not in storage.mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    del storage.mines[mine_id]
    return {"message": "Mine deleted successfully"}
