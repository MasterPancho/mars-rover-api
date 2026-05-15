from pydantic import BaseModel, Field
from typing import Optional


class MapUpdate(BaseModel):
    width: int
    height: int

class MineCreate(BaseModel):
    x: int
    y: int
    serial_number: str = Field(max_length=50)

class MineUpdate(BaseModel):
    x: Optional[int] = None
    y: Optional[int] = None
    serial_number: Optional[str] = Field(None, max_length=50)

class RoverCreate(BaseModel):
    commands: str = Field(max_length=200)

class RoverUpdate(BaseModel):
    commands: str = Field(max_length=200)
