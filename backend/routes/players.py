"""
Player routes — registration, listing, stats, edit, delete.
"""
from fastapi import APIRouter, HTTPException
from database import find_all, find_one, insert_one, update_one, delete_one
from models import PlayerCreate

router = APIRouter(prefix="/api/players", tags=["players"])


@router.post("")
async def create_player(p: PlayerCreate):
    existing = find_one("players", {"email": p.email})
    if existing:
        raise HTTPException(400, "A player with this email already exists")
    doc = insert_one("players", {
        "name": p.name,
        "email": p.email,
        "avatar_color": p.avatar_color,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "total_score": 0,
        "matches_played": 0,
    })
    return doc


@router.get("")
async def list_players():
    return find_all("players", sort_key="total_score", sort_reverse=True)


@router.get("/{pid}")
async def get_player(pid: str):
    doc = find_one("players", {"id": pid})
    if not doc:
        raise HTTPException(404, "Player not found")
    doc["recent_matches"] = find_all("matches", {
        "$or": [{"player_white_id": pid}, {"player_black_id": pid}]
    }, sort_key="created_at", sort_reverse=True, limit=10)
    return doc


@router.put("/{pid}")
async def update_player(pid: str, p: PlayerCreate):
    player = find_one("players", {"id": pid})
    if not player:
        raise HTTPException(404, "Player not found")
    update_one("players", {"id": pid}, {
        "name": p.name,
        "email": p.email,
        "avatar_color": p.avatar_color,
    })
    return {"success": True}


@router.delete("/{pid}")
async def delete_player(pid: str):
    ok = delete_one("players", {"id": pid})
    if not ok:
        raise HTTPException(404, "Player not found")
    return {"success": True}
