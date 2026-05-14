import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from storage import mines, mine_id_counter, map_data, rovers, rover_id_counter
from models import MineCreate, MineUpdate, RoverCreate, RoverUpdate, MapUpdate

load_dotenv()

# ── Security config ────────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")

MAX_ROVERS  = 10
MAX_MINES   = 50
MAX_MAP_DIM = 100

# ── Rate limiter (per client IP) ───────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API key dependency ─────────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(key: str = Depends(_api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="Server API key not configured")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

AUTH = Depends(require_api_key)

# ── Rover direction helpers ────────────────────────────────────────────────────
directions = ["N", "E", "S", "W"]

def turn_left(current):
    return directions[(directions.index(current) - 1) % 4]

def turn_right(current):
    return directions[(directions.index(current) + 1) % 4]

def move_forward(rover):
    new_x, new_y = rover["x"], rover["y"]
    if rover["direction"] == "N": new_y -= 1
    elif rover["direction"] == "S": new_y += 1
    elif rover["direction"] == "E": new_x += 1
    elif rover["direction"] == "W": new_x -= 1
    if new_x < 0 or new_x >= map_data["width"] or new_y < 0 or new_y >= map_data["height"]:
        return False
    rover["x"], rover["y"] = new_x, new_y
    return True

def find_mine(x, y):
    for mine_id, mine in mines.items():
        if mine["x"] == x and mine["y"] == y:
            return mine_id
    return None

# ── Static UI ──────────────────────────────────────────────────────────────────
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
async def read_index():
    return RedirectResponse(url="/ui/index.html")

######## MAP ROUTES ########

@app.get("/map", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_map(request: Request):
    return {"width": map_data["width"], "height": map_data["height"], "mines": list(mines.values())}

@app.put("/map", dependencies=[AUTH])
@limiter.limit("10/minute")
def update_map(request: Request, data: MapUpdate):
    if not (1 <= data.width <= MAX_MAP_DIM) or not (1 <= data.height <= MAX_MAP_DIM):
        raise HTTPException(status_code=400, detail=f"Dimensions must be between 1 and {MAX_MAP_DIM}")
    map_data["width"] = data.width
    map_data["height"] = data.height
    return map_data

######## MINES ROUTES ########

@app.get("/mines", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_mines(request: Request):
    return list(mines.values())

@app.get("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_mine(request: Request, mine_id: int):
    if mine_id not in mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    return mines[mine_id]

@app.post("/mines", dependencies=[AUTH])
@limiter.limit("30/minute")
def create_mine(request: Request, mine: MineCreate):
    global mine_id_counter
    if len(mines) >= MAX_MINES:
        raise HTTPException(status_code=400, detail=f"Mine limit reached ({MAX_MINES} max)")
    if mine.x < 0 or mine.y < 0 or mine.x >= map_data["width"] or mine.y >= map_data["height"]:
        raise HTTPException(status_code=400, detail="Coordinates out of map bounds")
    new_mine = {"id": mine_id_counter, "x": mine.x, "y": mine.y, "serial_number": mine.serial_number}
    mines[mine_id_counter] = new_mine
    mine_id_counter += 1
    return {"id": new_mine["id"]}

@app.put("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("20/minute")
def update_mine(request: Request, mine_id: int, mine_update: MineUpdate):
    if mine_id not in mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    mine = mines[mine_id]
    if mine_update.x is not None:
        if mine_update.x < 0 or mine_update.x >= map_data["width"]:
            raise HTTPException(status_code=400, detail="Invalid X coordinate")
        mine["x"] = mine_update.x
    if mine_update.y is not None:
        if mine_update.y < 0 or mine_update.y >= map_data["height"]:
            raise HTTPException(status_code=400, detail="Invalid Y coordinate")
        mine["y"] = mine_update.y
    if mine_update.serial_number is not None:
        mine["serial_number"] = mine_update.serial_number
    return mine

@app.delete("/mines/{mine_id}", dependencies=[AUTH])
@limiter.limit("30/minute")
def delete_mine(request: Request, mine_id: int):
    if mine_id not in mines:
        raise HTTPException(status_code=404, detail="Mine not found")
    del mines[mine_id]
    return {"message": "Mine deleted successfully"}

######## ROVER ROUTES ########

@app.get("/rovers", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_rovers(request: Request):
    return [{"id": r["id"], "status": r["status"]} for r in rovers.values()]

@app.get("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("60/minute")
def get_rover(request: Request, rover_id: int):
    if rover_id not in rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    return rovers[rover_id]

@app.post("/rovers", dependencies=[AUTH])
@limiter.limit("10/minute")
def create_rover(request: Request, rover: RoverCreate):
    global rover_id_counter
    if len(rovers) >= MAX_ROVERS:
        raise HTTPException(status_code=400, detail=f"Rover limit reached ({MAX_ROVERS} max)")
    valid = {"L", "R", "M", "D"}
    for c in rover.commands:
        if c not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid command: {c}")
    new_rover = {
        "id": rover_id_counter,
        "status": "Not Started",
        "x": 0, "y": 0,
        "direction": "S",
        "commands": rover.commands,
        "executed_commands": []
    }
    rovers[rover_id_counter] = new_rover
    rover_id_counter += 1
    return {"id": new_rover["id"]}

@app.put("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("20/minute")
def update_rover_commands(request: Request, rover_id: int, update: RoverUpdate):
    if rover_id not in rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    if rovers[rover_id]["status"] not in ["Not Started", "Finished"]:
        raise HTTPException(status_code=400, detail="Rover cannot be updated right now")
    rovers[rover_id]["commands"] = update.commands
    return rovers[rover_id]

@app.post("/rovers/{rover_id}/dispatch", dependencies=[AUTH])
@limiter.limit("20/minute")
def dispatch_rover(request: Request, rover_id: int):
    if rover_id not in rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    rover = rovers[rover_id]
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
                del mines[mine_id]
        else:
            raise HTTPException(status_code=400, detail=f"Invalid command: {cmd}")
        rover["executed_commands"].append(cmd)

    rover["status"] = "Finished"
    return {
        "id": rover["id"], "status": rover["status"],
        "latest_position": {"x": rover["x"], "y": rover["y"]},
        "executed_commands": rover["executed_commands"], "path": path
    }

@app.delete("/rovers/{rover_id}", dependencies=[AUTH])
@limiter.limit("10/minute")
def delete_rover(request: Request, rover_id: int):
    if rover_id not in rovers:
        raise HTTPException(status_code=404, detail="Rover not found")
    del rovers[rover_id]
    return {"message": "Rover deleted successfully"}

######## WEBSOCKET ########

@app.websocket("/ws/rovers/{rover_id}/control")
async def rover_ws(websocket: WebSocket, rover_id: int, api_key: str = Query("")):
    if api_key != API_KEY:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    rover = rovers.get(rover_id)
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
                    res["PIN"], _ = mines[m_id]["serial_number"], mines.pop(m_id)
            elif cmd == "L":
                rover["direction"] = turn_left(rover["direction"])
            elif cmd == "R":
                rover["direction"] = turn_right(rover["direction"])

            rover["executed_commands"].append(cmd)
            await websocket.send_json(res)

    except WebSocketDisconnect:
        if rover["status"] != "Eliminated":
            rover["status"] = "Finished"
