import random
import math
from itertools import combinations
from fastapi import APIRouter, HTTPException, Depends
from database import find_all, find_one, insert_one, update_one, push_to_array, pull_from_array, delete_one
from models import TournamentCreate, Registration
import auth

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])

@router.post("")
async def create_tournament(t: TournamentCreate, admin: dict = Depends(auth.get_admin_user)):
    doc = await insert_one("tournaments", {
        "name": t.name,
        "format": t.format,
        "status": "upcoming",
        "registered_players": [],
        "rounds": [],
        "board_size": 7,
    })
    doc["player_count"] = 0
    return doc

@router.get("")
async def list_tournaments():
    items = await find_all("tournaments", sort_key="created_at", sort_reverse=True)
    for t in items:
        t["player_count"] = len(t.get("registered_players", []))
    return items

@router.get("/{tid}")
async def get_tournament(tid: str):
    doc = await find_one("tournaments", {"id": tid})
    if not doc:
        raise HTTPException(404, "Tournament not found")
    doc["player_count"] = len(doc.get("registered_players", []))
    
    matches = await find_all("matches", {"tournament_id": tid}, sort_key="created_at")
    for m in matches:
        for key in ["player_white_id", "player_black_id"]:
            pid = m.get(key)
            name_key = key.replace("_id", "_name")
            if pid == "BYE":
                m[name_key] = "BYE"
            elif pid and pid.startswith("bot:"):
                bot = await find_one("bots", {"id": pid[4:]})
                m[name_key] = f"🤖 {bot['name']}" if bot else "Unknown Bot"
            else:
                m[name_key] = "Unknown"
    doc["matches"] = matches
    return doc

@router.put("/{tid}")
async def update_tournament_status(tid: str, status: str, admin: dict = Depends(auth.get_admin_user)):
    valid = {"upcoming", "active", "completed"}
    if status not in valid: raise HTTPException(400, "Invalid status")
    ok = await update_one("tournaments", {"id": tid}, {"status": status})
    if not ok: raise HTTPException(404, "Tournament not found")
    return {"success": True}

@router.delete("/{tid}")
async def delete_tournament(tid: str, admin: dict = Depends(auth.get_admin_user)):
    ok = await delete_one("tournaments", {"id": tid})
    if not ok: raise HTTPException(404, "Tournament not found")
    return {"success": True}

@router.post("/{tid}/register")
async def register_player(tid: str, player_id: str, current_user: dict = Depends(auth.get_current_user)):
    t = await find_one("tournaments", {"id": tid})
    if not t: raise HTTPException(404, "Tournament not found")
    if player_id != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You can only register yourself")
        
    if player_id in t.get("registered_players", []):
        raise HTTPException(400, "Player already registered")
        
    await push_to_array("tournaments", {"id": tid}, "registered_players", player_id)
    return {"success": True}

@router.post("/{tid}/register-bot")
async def register_bot(tid: str, bot_id: str, current_user: dict = Depends(auth.get_current_user)):
    t = await find_one("tournaments", {"id": tid})
    if not t: raise HTTPException(404, "Tournament not found")
    bot = await find_one("bots", {"id": bot_id})
    if not bot: raise HTTPException(404, "Bot not found")
    if bot.get("owner_id") != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You can only register your own bots")
        
    prefixed = f"bot:{bot_id}"
    if prefixed in t.get("registered_players", []):
        raise HTTPException(400, "Bot already registered")
        
    # Check if user already has a bot in this tournament
    for p in t.get("registered_players", []):
        if p.startswith("bot:"):
            b = await find_one("bots", {"id": p[4:]})
            if b and b.get("owner_id") == current_user["id"]:
                raise HTTPException(400, "You already have a bot registered in this tournament")
                
    await push_to_array("tournaments", {"id": tid}, "registered_players", prefixed)
    return {"success": True}

@router.post("/{tid}/unregister")
async def unregister_participant(tid: str, participant_id: str, current_user: dict = Depends(auth.get_current_user)):
    t = await find_one("tournaments", {"id": tid})
    if not t: raise HTTPException(404, "Tournament not found")
    if t.get("status") != "upcoming": raise HTTPException(400, "Tournament has already started")

    is_admin = current_user.get("role") == "ADMIN"
    
    # Check permissions
    if participant_id.startswith("bot:"):
        bot = await find_one("bots", {"id": participant_id[4:]})
        if not bot: raise HTTPException(404, "Bot not found")
        if not is_admin and bot.get("owner_id") != current_user["id"]:
            raise HTTPException(403, "Not authorized to unregister this bot")
    else:
        if not is_admin and participant_id != current_user["id"]:
            raise HTTPException(403, "Not authorized to unregister this player")

    if participant_id not in t.get("registered_players", []):
        raise HTTPException(400, "Participant not registered")

    await pull_from_array("tournaments", {"id": tid}, "registered_players", participant_id)
    return {"success": True}

@router.post("/{tid}/generate-bracket")
async def generate_bracket(tid: str, admin: dict = Depends(auth.get_admin_user)):
    t = await find_one("tournaments", {"id": tid})
    if not t: raise HTTPException(404, "Tournament not found")
    
    participants = t.get("registered_players", [])
    if len(participants) < 1: raise HTTPException(400, "Need at least 1 participant")
    if t.get("rounds"): raise HTTPException(400, "Bracket already generated")
    
    random.shuffle(participants)
    n = len(participants)
    total_rounds = max(1, math.ceil(math.log2(n)))
    bracket_size = 2 ** total_rounds
    padded = participants + ["BYE"] * (bracket_size - n)
    
    round1_ids = []
    for i in range(0, bracket_size, 2):
        p1, p2 = padded[i], padded[i + 1]
        is_bye = (p2 == "BYE")
        match_doc = await insert_one("matches", {
            "tournament_id": tid,
            "player_white_id": p1,
            "player_black_id": p2,
            "board_size": t.get("board_size", 7),
            "round_num": 0,
            "match_index": i // 2,
            "status": "completed" if is_bye else "scheduled",
            "white_score": 0, "black_score": 0,
            "winner": "white" if is_bye else None,
        })
        round1_ids.append(match_doc["id"])
        
    rounds = [round1_ids] + [[] for _ in range(total_rounds - 1)]
    await update_one("tournaments", {"id": tid}, {
        "status": "active",
        "rounds": rounds,
        "total_rounds": total_rounds,
    })
    
    # Check for BYEs advancing immediately
    r1_matches = await find_all("matches", {"tournament_id": tid, "round_num": 0})
    if all(m.get("status") == "completed" for m in r1_matches):
        from routes.matches import _advance_bracket
        await _advance_bracket(tid, r1_matches[0])
        
    return {"success": True, "total_rounds": total_rounds, "round1_matches": len(round1_ids)}
