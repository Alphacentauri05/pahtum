from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

# Roles
class Role(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"

# User Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: Role
    created_at: str

class UserInDB(UserResponse):
    password_hash: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Bot Models
class BotCreate(BaseModel):
    name: str
    description: str = ""

class BotResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    active: bool
    created_at: str

# Tournament Models
class TournamentCreate(BaseModel):
    name: str
    format: str = "single_elimination"

class TournamentResponse(BaseModel):
    id: str
    name: str
    format: str
    status: str
    created_at: str

class Registration(BaseModel):
    bot_id: str

# Match & Game Models
class MatchCreate(BaseModel):
    tournament_id: Optional[str] = None
    player_white_id: str
    player_black_id: str
    board_size: int = 7
    round_num: int = 0
    match_index: int = 0

class GameCreate(BaseModel):
    board_size: int = 7
    mode: str
    player_white: str
    player_black: str
    bot_white_id: Optional[str] = None
    bot_black_id: Optional[str] = None
    match_id: Optional[str] = None

class MoveRequest(BaseModel):
    row: int
    col: int
