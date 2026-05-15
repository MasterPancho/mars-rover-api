import os
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from .. import storage
from ..models import RoverCreate, RoverUpdate
from ..auth import AUTH
from ..limiter import limiter
from ..rover import turn_left, turn_right, move_forward, find_mine

MAX_ROVERS = 10

router = APIRouter()


@router.get("/rovers", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_rovers(request: Request):
    return [{"id": r["id"], "status": r["status"]} for r in storage.rovers.values()]


@router.get("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_rover(request: Request, rover_id: int):
    if rover_id not in storage.rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    return storage.rovers[rover_id]


@router.post("/rovers", dependencies=[AUTH])
@limiter.limit("10/minute")
def create_rover(request: Request, rover: RoverCreate):
    if len(storage.rovers) >= MAX_ROVERS:
        raise HTTPException(status_code=400, detail=f"Rover limit reached ({MAX_ROVERS} max)")
    valid = {"L", "R", "M", "D"}
    for c in rover.commands:
        if c not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid command: {c}")
    new_rover = {
        "id": storage.rover_id_counter,
        "status": "Not Started",
        "x": 0, "y": 0,
        "direction": "S",
        "commands": rover.commands,
        "executed_commands": []
    }
    storage.rovers[storage.rover_id_counter] = new_rover
    storage.rover_id_counter += 1
    return {"id": new_rover["id"]}


@router.put("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("20/minute")
def update_rover_commands(request: Request, rover_id: int, update: RoverUpdate):
    if rover_id not in storage.rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    if storage.rovers[rover_id]["status"] not in ["Not Started", "Finished"]:
        raise HTTPException(status_code=400, detail="Rover cannot be updated right now")
    storage.rovers[rover_id]["commands"] = update.commands
    return storage.rovers[rover_id]


@router.post("/rovers/{rover_id}/dispatch", dependencies=[AUTH])
@limiter.limit("20/minute")
def dispatch_rover(request: Request, rover_id: int):
    if rover_id not in storage.rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    rover = storage.rovers[rover_id]
    rover["status"] = "Moving"
    rover["executed_commands"] = []
    path = [{"x": rover["x"], "y": rover["y"]}]

    for cmd in rover["commands"]:
        if cmd == "L":
            rover["direction"] = turn_left(rover["direction"])
        elif cmd == "R":
            rover["direction"] = turn_right(rover["direction"])
        elif cmd == "M":
            mine_id = find_mine(rover["x"], rover["y"])
            if mine_id is not None:
                rover["status"] = "Eliminated"
                rover["executed_commands"].append(cmd)
                return {
                    "id": rover["id"], "status": rover["status"],
                    "latest_position": {"x": rover["x"], "y": rover["y"]},
                    "executed_commands": rover["executed_commands"], "path": path
                }
            if move_forward(rover):
                path.append({"x": rover["x"], "y": rover["y"]})
        elif cmd == "D":
            mine_id = find_mine(rover["x"], rover["y"])
            if mine_id is not None:
                del storage.mines[mine_id]
        else:
            raise HTTPException(status_code=400, detail=f"Invalid command: {cmd}")
        rover["executed_commands"].append(cmd)

    rover["status"] = "Finished"
    return {
        "id": rover["id"], "status": rover["status"],
        "latest_position": {"x": rover["x"], "y": rover["y"]},
        "executed_commands": rover["executed_commands"], "path": path
    }


@router.delete("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("10/minute")
def delete_rover(request: Request, rover_id: int):
    if rover_id not in storage.rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    del storage.rovers[rover_id]
    return {"message": "Rover deleted successfully"}


@router.websocket("/ws/rovers/{rover_id}/control")
async def rover_ws(websocket: WebSocket, rover_id: int, api_key: str = Query("")):
    if api_key != os.getenv("API_KEY", ""):
        await websocket.close(code=4001)
        return

    await websocket.accept()
    rover = storage.rovers.get(rover_id)
    if not rover or rover["status"] not in ["Not Started", "Finished"]:
        await websocket.send_json({"error": "Busy or Not Found"})
        await websocket.close()
        return

    rover["status"], rover["executed_commands"] = "Moving", []

    try:
        while True:
            cmd = await websocket.receive_text()
            if len(cmd) != 1 or cmd not in {"M", "L", "R", "D"}:
                await websocket.send_json({"error": f"Invalid command: {cmd}"})
                continue

            res = {"command": cmd, "success": True}

            if cmd == "M":
                if find_mine(rover["x"], rover["y"]):
                    rover["status"] = "Eliminated"
                    await websocket.send_json({"status": "Eliminated", "x": rover["x"], "y": rover["y"]})
                    break
                if move_forward(rover):
                    res.update({"x": rover["x"], "y": rover["y"]})
            elif cmd == "D":
                m_id = find_mine(rover["x"], rover["y"])
                if m_id:
                    res["PIN"], _ = storage.mines[m_id]["serial_number"], storage.mines.pop(m_id)
            elif cmd == "L":
                rover["direction"] = turn_left(rover["direction"])
            elif cmd == "R":
                rover["direction"] = turn_right(rover["direction"])

            rover["executed_commands"].append(cmd)
            await websocket.send_json(res)

    except WebSocketDisconnect:
        if rover["status"] != "Eliminated":
            rover["status"] = "Finished"
