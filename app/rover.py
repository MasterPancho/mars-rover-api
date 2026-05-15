from . import storage

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
    if new_x < 0 or new_x >= storage.map_data["width"] or new_y < 0 or new_y >= storage.map_data["height"]:
        return False
    rover["x"], rover["y"] = new_x, new_y
    return True

def find_mine(x, y):
    for mine_id, mine in storage.mines.items():
        if mine["x"] == x and mine["y"] == y:
            return mine_id
    return None
