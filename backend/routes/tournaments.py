import random
import math
from itertools import combinations
from fastapi import APIRouter, HTTPException
from database import find_all, find_one, insert_one, update_one, push_to_array, delete_one
from models import TournamentCreate

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])


@router.post("")
async def create_tournament(t: TournamentCreate):
    doc = insert_one("tournaments", {
        "name": t.name,
        "description": t.description,
        "board_size": t.board_size,
        "status": "upcoming",
        "format": t.format,           # "knockout" or "group_stage"
        "max_players": t.max_players,
        "registered_players": [],
        "rounds": [],
        "start_date": t.start_date,
        # Group-stage specific fields
        "groups": {},                  # {"A": [...ids], "B": [...ids]}
        "phase": 0,                   # 0=not started, 1=group phase, 2=finals
        "phase2_status": None,        # None, "swap_window", "active", "done"
        "phase2_participants": [],     # IDs that advanced
    })
    doc["player_count"] = 0
    return doc


@router.get("")
async def list_tournaments():
    items = find_all("tournaments", sort_key="created_at", sort_reverse=True)
    for t in items:
        t["player_count"] = len(t.get("registered_players", []))
    return items


@router.get("/{tid}")
async def get_tournament(tid: str):
    doc = find_one("tournaments", {"id": tid})
    if not doc:
        raise HTTPException(404, "Tournament not found")
    doc["player_count"] = len(doc.get("registered_players", []))

    # Fetch all matches for this tournament, enriched with participant names
    matches = find_all("matches", {"tournament_id": tid}, sort_key="created_at")
    for m in matches:
        for key in ["player_white_id", "player_black_id"]:
            pid = m.get(key)
            name_key = key.replace("_id", "_name")
            if pid == "BYE":
                m[name_key] = "BYE"
            elif pid and pid.startswith("bot:"):
                bot = find_one("bots", {"id": pid[4:]})
                m[name_key] = f"🤖 {bot['name']}" if bot else "Unknown Bot"
            elif pid and pid != "AI":
                p = find_one("players", {"id": pid})
                m[name_key] = p["name"] if p else "Unknown"
            else:
                m[name_key] = "AI Bot"
    doc["matches"] = matches
    return doc


@router.put("/{tid}")
async def update_tournament_status(tid: str, status: str):
    valid = {"upcoming", "active", "completed"}
    if status not in valid:
        raise HTTPException(400, f"Status must be one of {valid}")
    ok = update_one("tournaments", {"id": tid}, {"status": status})
    if not ok:
        raise HTTPException(404, "Tournament not found")
    return {"success": True}


@router.put("/{tid}/edit")
async def edit_tournament(tid: str, t: TournamentCreate):
    tournament = find_one("tournaments", {"id": tid})
    if not tournament:
        raise HTTPException(404, "Tournament not found")
    update_one("tournaments", {"id": tid}, {
        "name": t.name,
        "description": t.description,
        "board_size": t.board_size,
        "max_players": t.max_players,
        "format": t.format,
    })
    return {"success": True}


@router.delete("/{tid}")
async def delete_tournament(tid: str):
    ok = delete_one("tournaments", {"id": tid})
    if not ok:
        raise HTTPException(404, "Tournament not found")
    return {"success": True}


@router.post("/{tid}/register")
async def register_player(tid: str, player_id: str):
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    if player_id in t.get("registered_players", []):
        raise HTTPException(400, "Already registered")
    if len(t.get("registered_players", [])) >= t.get("max_players", 16):
        raise HTTPException(400, "Tournament is full")
    push_to_array("tournaments", {"id": tid}, "registered_players", player_id)
    return {"success": True}


@router.post("/{tid}/register-bot")
async def register_bot(tid: str, bot_id: str):
    """Register a bot in the tournament. Stored with 'bot:' prefix."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    bot = find_one("bots", {"id": bot_id})
    if not bot:
        raise HTTPException(404, "Bot not found")
    prefixed = f"bot:{bot_id}"
    if prefixed in t.get("registered_players", []):
        raise HTTPException(400, "Bot already registered")
    if len(t.get("registered_players", [])) >= t.get("max_players", 16):
        raise HTTPException(400, "Tournament is full")
    push_to_array("tournaments", {"id": tid}, "registered_players", prefixed)
    return {"success": True}


def _participant_name(pid: str) -> str:
    """Get display name for a participant (player or bot)."""
    if pid == "BYE":
        return "BYE"
    if pid.startswith("bot:"):
        bot = find_one("bots", {"id": pid[4:]})
        return f"🤖 {bot['name']}" if bot else "Unknown Bot"
    p = find_one("players", {"id": pid})
    return p["name"] if p else "Unknown"


# ==========================================
# KNOCKOUT BRACKET (existing)
# ==========================================

@router.post("/{tid}/generate-bracket")
async def generate_bracket(tid: str):
    """Generate a knockout bracket from registered players and bots."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")

    participants = t.get("registered_players", [])
    if len(participants) < 2:
        raise HTTPException(400, "Need at least 2 participants (players or bots)")

    if t.get("rounds") and len(t["rounds"]) > 0:
        raise HTTPException(400, "Bracket already generated")

    # Shuffle for random seeding
    random.shuffle(participants)

    # Calculate total rounds needed
    n = len(participants)
    total_rounds = math.ceil(math.log2(n))
    bracket_size = 2 ** total_rounds

    # Pad with BYEs
    padded = participants + ["BYE"] * (bracket_size - n)

    # Create Round 1 matches
    round1_ids = []
    for i in range(0, bracket_size, 2):
        p1, p2 = padded[i], padded[i + 1]
        is_bye = p2 == "BYE"
        match_doc = insert_one("matches", {
            "tournament_id": tid,
            "player_white_id": p1,
            "player_black_id": p2,
            "board_size": t.get("board_size", 7),
            "round_num": 0,
            "match_index": i // 2,
            "status": "completed" if is_bye else "scheduled",
            "white_score": 0,
            "black_score": 0,
            "winner": "white" if is_bye else None,
            "moves": [],
            "final_board": None,
            "played_at": None,
        })
        round1_ids.append(match_doc["id"])

    # Initialize rounds array
    rounds = [round1_ids] + [[] for _ in range(total_rounds - 1)]

    # Update tournament
    update_one("tournaments", {"id": tid}, {
        "status": "active",
        "rounds": rounds,
        "total_rounds": total_rounds,
    })

    # If all round 1 matches are BYEs, advance
    r1_matches = find_all("matches", {"tournament_id": tid, "round_num": 0})
    if all(m.get("status") == "completed" for m in r1_matches):
        from routes.matches import _advance_bracket
        _advance_bracket(tid, r1_matches[0])

    return {
        "success": True,
        "total_rounds": total_rounds,
        "round1_matches": len(round1_ids),
        "byes": bracket_size - n,
    }


# ==========================================
# GROUP STAGE (new)
# ==========================================

@router.post("/{tid}/generate-groups")
async def generate_groups(tid: str):
    """
    Split participants into Group A and Group B.
    Generate all round-robin matches within each group (Phase 1).
    """
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    if t.get("format") != "group_stage":
        raise HTTPException(400, "Tournament is not group_stage format")
    if t.get("phase", 0) != 0:
        raise HTTPException(400, "Groups already generated")

    participants = list(t.get("registered_players", []))
    if len(participants) < 4:
        raise HTTPException(400, "Need at least 4 participants for group stage")

    random.shuffle(participants)

    # Split into two groups. If odd, group B gets the extra team.
    mid = len(participants) // 2
    group_a = participants[:mid]
    group_b = participants[mid:]

    # Generate round-robin matches for both groups
    board_size = t.get("board_size", 7)
    all_match_ids = []
    match_idx = 0

    for group_name, members in [("A", group_a), ("B", group_b)]:
        for p1, p2 in combinations(members, 2):
            match_doc = insert_one("matches", {
                "tournament_id": tid,
                "player_white_id": p1,
                "player_black_id": p2,
                "board_size": board_size,
                "round_num": 0,
                "match_index": match_idx,
                "group": group_name,
                "phase": 1,
                "status": "scheduled",
                "white_score": 0,
                "black_score": 0,
                "winner": None,
                "moves": [],
                "final_board": None,
                "played_at": None,
            })
            all_match_ids.append(match_doc["id"])
            match_idx += 1

    # Update tournament
    update_one("tournaments", {"id": tid}, {
        "status": "active",
        "phase": 1,
        "groups": {"A": group_a, "B": group_b},
        "rounds": [all_match_ids],
    })

    return {
        "success": True,
        "group_a": [_participant_name(p) for p in group_a],
        "group_b": [_participant_name(p) for p in group_b],
        "total_matches": len(all_match_ids),
    }


def _group_standings(tid: str, group_name: str, phase: int = 1) -> list[dict]:
    """Calculate standings for a group based on match results."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        return []

    if phase == 1:
        members = t.get("groups", {}).get(group_name, [])
    else:
        members = t.get("phase2_participants", [])

    query = {"tournament_id": tid, "phase": phase}
    if phase == 1:
        query["group"] = group_name

    matches = find_all("matches", query)

    stats = {}
    for pid in members:
        stats[pid] = {
            "id": pid,
            "name": _participant_name(pid),
            "played": 0, "wins": 0, "losses": 0, "draws": 0,
            "points": 0, "score_for": 0, "score_against": 0,
        }

    for m in matches:
        if m.get("status") != "completed":
            continue
        w_id = m["player_white_id"]
        b_id = m["player_black_id"]
        w_score = m.get("white_score", 0)
        b_score = m.get("black_score", 0)
        winner = m.get("winner")

        for pid, my_score, opp_score, role in [
            (w_id, w_score, b_score, "white"),
            (b_id, b_score, w_score, "black"),
        ]:
            if pid not in stats:
                continue
            stats[pid]["played"] += 1
            stats[pid]["score_for"] += my_score
            stats[pid]["score_against"] += opp_score
            if winner == role:
                stats[pid]["wins"] += 1
                stats[pid]["points"] += 3
            elif winner == "draw":
                stats[pid]["draws"] += 1
                stats[pid]["points"] += 1
            else:
                stats[pid]["losses"] += 1

    standings = list(stats.values())
    standings.sort(key=lambda s: (
        -s["points"],
        -(s["score_for"] - s["score_against"]),
        -s["score_for"],
    ))
    return standings


@router.get("/{tid}/standings")
async def get_standings(tid: str):
    """Get group standings for a group_stage tournament."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")

    result = {}
    if t.get("format") == "group_stage":
        result["group_a"] = _group_standings(tid, "A", phase=1)
        result["group_b"] = _group_standings(tid, "B", phase=1)
        if t.get("phase", 0) >= 2:
            result["phase2"] = _group_standings(tid, "final", phase=2)
    return result


@router.post("/{tid}/advance-to-phase2")
async def advance_to_phase2(tid: str, top_n: int = 4):
    """
    Advance top N teams from each group to Phase 2.
    Opens the bot swap window.
    """
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    if t.get("format") != "group_stage":
        raise HTTPException(400, "Not a group_stage tournament")
    if t.get("phase") != 1:
        raise HTTPException(400, "Tournament is not in Phase 1")

    # Check all Phase 1 matches are done
    p1_matches = find_all("matches", {"tournament_id": tid, "phase": 1})
    if not all(m.get("status") == "completed" for m in p1_matches):
        raise HTTPException(400, "Not all Phase 1 matches are completed yet")

    # Get top N from each group
    standings_a = _group_standings(tid, "A", phase=1)
    standings_b = _group_standings(tid, "B", phase=1)

    # Take top_n from each, or all if group is smaller
    qualifiers_a = [s["id"] for s in standings_a[:top_n]]
    qualifiers_b = [s["id"] for s in standings_b[:top_n]]
    all_qualifiers = qualifiers_a + qualifiers_b

    if len(all_qualifiers) < 2:
        raise HTTPException(400, "Not enough qualifiers for Phase 2")

    update_one("tournaments", {"id": tid}, {
        "phase": 2,
        "phase2_status": "swap_window",
        "phase2_participants": all_qualifiers,
    })

    return {
        "success": True,
        "qualifiers": [_participant_name(p) for p in all_qualifiers],
        "total": len(all_qualifiers),
    }


@router.post("/{tid}/swap-bot")
async def swap_bot(tid: str, participant_id: str, new_bot_id: str):
    """During swap window, let a participant change their bot."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    if t.get("phase2_status") != "swap_window":
        raise HTTPException(400, "Swap window is not open")

    new_bot = find_one("bots", {"id": new_bot_id})
    if not new_bot:
        raise HTTPException(404, "New bot not found")

    new_prefixed = f"bot:{new_bot_id}"
    participants = t.get("phase2_participants", [])

    if participant_id not in participants:
        raise HTTPException(400, "Participant is not in Phase 2")

    # Replace the participant's entry
    idx = participants.index(participant_id)
    participants[idx] = new_prefixed

    # Also update in registered_players
    reg = t.get("registered_players", [])
    if participant_id in reg:
        reg_idx = reg.index(participant_id)
        reg[reg_idx] = new_prefixed

    update_one("tournaments", {"id": tid}, {
        "phase2_participants": participants,
        "registered_players": reg,
    })

    return {"success": True, "new_participant": _participant_name(new_prefixed)}


@router.post("/{tid}/start-phase2")
async def start_phase2(tid: str):
    """Close swap window and generate Phase 2 round-robin matches."""
    t = find_one("tournaments", {"id": tid})
    if not t:
        raise HTTPException(404, "Tournament not found")
    if t.get("phase2_status") != "swap_window":
        raise HTTPException(400, "Swap window is not open")

    participants = t.get("phase2_participants", [])
    if len(participants) < 2:
        raise HTTPException(400, "Not enough participants for Phase 2")

    # Generate round-robin matches for Phase 2
    board_size = t.get("board_size", 7)
    match_ids = []
    match_idx = 0

    for p1, p2 in combinations(participants, 2):
        match_doc = insert_one("matches", {
            "tournament_id": tid,
            "player_white_id": p1,
            "player_black_id": p2,
            "board_size": board_size,
            "round_num": 1,
            "match_index": match_idx,
            "group": "final",
            "phase": 2,
            "status": "scheduled",
            "white_score": 0,
            "black_score": 0,
            "winner": None,
            "moves": [],
            "final_board": None,
            "played_at": None,
        })
        match_ids.append(match_doc["id"])
        match_idx += 1

    # Update tournament
    rounds = t.get("rounds", [])
    rounds.append(match_ids)
    update_one("tournaments", {"id": tid}, {
        "phase2_status": "active",
        "rounds": rounds,
    })

    return {
        "success": True,
        "phase2_matches": len(match_ids),
    }
