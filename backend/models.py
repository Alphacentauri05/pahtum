"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ---------- Players ----------
class PlayerCreate(BaseModel):
    name: str
    email: str
    avatar_color: str = "#6366f1"


class PlayerOut(BaseModel):
    id: str
    name: str
    email: str
    avatar_color: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_score: int = 0
    matches_played: int = 0
    created_at: datetime


# ---------- Tournaments ----------
class TournamentCreate(BaseModel):
    name: str
    description: str = ""
    board_size: int = 7
    max_players: int = 16
    start_date: Optional[str] = None
    format: str = "knockout"  # "knockout" or "group_stage"


class TournamentOut(BaseModel):
    id: str
    name: str
    description: str
    board_size: int
    status: str
    max_players: int
    registered_players: list[str]
    player_count: int = 0
    created_at: datetime
    start_date: Optional[str] = None


# ---------- Matches ----------
class MatchCreate(BaseModel):
    tournament_id: Optional[str] = None
    player_white_id: str
    player_black_id: str  # can be "AI"
    board_size: int = 7
    round_num: int = 0
    match_index: int = 0


class MatchOut(BaseModel):
    id: str
    tournament_id: Optional[str]
    player_white_id: str
    player_black_id: str
    player_white_name: str = ""
    player_black_name: str = ""
    board_size: int
    status: str
    white_score: int = 0
    black_score: int = 0
    winner: Optional[str] = None
    moves: list[dict] = []
    played_at: Optional[datetime] = None
    created_at: datetime


# ---------- Bots ----------
class BotCreate(BaseModel):
    name: str
    api_url: str
    owner: str = ""
    description: str = ""


class LocalBotCreate(BaseModel):
    """Register a local Python bot (module + function) instead of an HTTP URL."""
    name: str
    module: str  # e.g. "team7" or "team_bots.team7_algo1"
    entry_function: str = "bot_move"
    owner: str = ""
    description: str = ""


# ---------- Game ----------
class GameCreate(BaseModel):
    board_size: int = 7
    mode: str = "pvp"  # "pvp", "vs_ai", or "bot_vs_bot"
    player_white: str = "Player 1"
    player_black: str = "Player 2"
    match_id: Optional[str] = None
    bot_white_id: Optional[str] = None
    bot_black_id: Optional[str] = None


class MoveRequest(BaseModel):
    row: int
    col: int
