from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from database import find_all, find_one, insert_one, update_one, update_inc
from models import MatchCreate

router = APIRouter(prefix="/api/matches", tags=["matches"])

@router.post("")
async def create_match(m: MatchCreate):
    doc = await insert_one("matches", {
        "tournament_id": m.tournament_id,
        "player_white_id": m.player_white_id,
        "player_black_id": m.player_black_id,
        "board_size": m.board_size,
        "round_num": m.round_num,
        "match_index": m.match_index,
        "status": "scheduled",
        "white_score": 0,
        "black_score": 0,
        "winner": None,
        "moves": [],
        "final_board": None,
        "played_at": None,
    })
    return doc

@router.get("")
async def list_matches(tournament_id: str = None, limit: int = 50):
    query = {"tournament_id": tournament_id} if tournament_id else {}
    results = await find_all("matches", query if query else None, sort_key="created_at", sort_reverse=True, limit=limit)
    for m in results:
        for key in ["player_white_id", "player_black_id"]:
            pid = m.get(key)
            name_key = key.replace("_id", "_name")
            if pid and pid != "AI" and pid != "BYE":
                p = await find_one("users", {"id": pid})
                m[name_key] = p["username"] if p else "Unknown"
            elif pid == "BYE":
                m[name_key] = "BYE"
            else:
                m[name_key] = "AI Bot"
    return results

@router.get("/{mid}")
async def get_match(mid: str):
    doc = await find_one("matches", {"id": mid})
    if not doc:
        raise HTTPException(404, "Match not found")
    return doc

@router.put("/{mid}/result")
async def update_match_result(mid: str, white_score: int, black_score: int,
                               winner: str, moves: list = None, final_board: list = None):
    match = await find_one("matches", {"id": mid})
    if not match:
        raise HTTPException(404, "Match not found")

    if winner == "draw":
        t = None
        if match.get("tournament_id"):
            t = await find_one("tournaments", {"id": match["tournament_id"]})
        if t and t.get("format", "knockout") != "group_stage":
            new_white = match.get("player_black_id")
            new_black = match.get("player_white_id")
            await update_one("matches", {"id": mid}, {
                "status": "scheduled",
                "player_white_id": new_white,
                "player_black_id": new_black,
                "white_score": 0,
                "black_score": 0,
                "winner": None,
                "moves": [],
                "final_board": None
            })
            return {"success": True, "message": "Match drawn! Colors swapped for a rematch."}

    upd = {
        "status": "completed",
        "white_score": white_score,
        "black_score": black_score,
        "winner": winner,
        "played_at": datetime.now(timezone.utc).isoformat(),
    }
    if moves is not None:
        upd["moves"] = moves
    if final_board is not None:
        upd["final_board"] = final_board

    ok = await update_one("matches", {"id": mid}, upd)
    
    # Reload match for stats
    match = await find_one("matches", {"id": mid})
    if match:
        for pid_key, score_key, role in [
            ("player_white_id", "white_score", "white"),
            ("player_black_id", "black_score", "black"),
        ]:
            pid = match.get(pid_key)
            if pid and pid not in ("AI", "BYE"):
                target_user_id = pid
                if pid.startswith("bot:"):
                    bot = await find_one("bots", {"id": pid[4:]})
                    if bot and bot.get("owner_id"):
                        target_user_id = bot["owner_id"]
                    else:
                        target_user_id = None
                
                if target_user_id:
                    inc = {"matches_played": 1, "total_score": match.get(score_key, 0)}
                    if winner == role:
                        inc["wins"] = 1
                    elif winner == "draw":
                        inc["draws"] = 1
                    else:
                        inc["losses"] = 1
                    await update_inc("users", {"id": target_user_id}, inc)

        if match.get("tournament_id"):
            t = await find_one("tournaments", {"id": match["tournament_id"]})
            if t and t.get("format") == "group_stage":
                phase = match.get("phase", 1)
                if phase == 2:
                    p2_matches = await find_all("matches", {
                        "tournament_id": match["tournament_id"],
                        "phase": 2,
                    })
                    if all(m.get("status") == "completed" for m in p2_matches):
                        await update_one("tournaments", {"id": match["tournament_id"]}, {
                            "status": "completed",
                            "phase2_status": "done",
                        })
            elif t and t.get("format", "knockout") == "knockout":
                await _advance_bracket(match["tournament_id"], match)

    return {"success": True}

async def _advance_bracket(tid: str, completed_match: dict):
    t = await find_one("tournaments", {"id": tid})
    if not t or t.get("status") == "completed":
        return

    rounds = t.get("rounds", [])
    round_num = completed_match.get("round_num", 0)

    round_matches = await find_all("matches", {
        "tournament_id": tid,
        "round_num": round_num,
    })

    all_done = all(m.get("status") == "completed" for m in round_matches)
    if not all_done:
        return

    total_rounds = len(rounds)
    if round_num >= total_rounds - 1:
        await update_one("tournaments", {"id": tid}, {"status": "completed"})
        return

    round_matches.sort(key=lambda m: m.get("match_index", 0))
    winners = []
    for m in round_matches:
        if m["winner"] == "white":
            winners.append(m["player_white_id"])
        elif m["winner"] == "black":
            winners.append(m["player_black_id"])
        else:
            winners.append(m["player_white_id"])

    next_round = round_num + 1
    next_match_ids = []
    for i in range(0, len(winners), 2):
        if i + 1 < len(winners):
            p1, p2 = winners[i], winners[i + 1]
        else:
            p1, p2 = winners[i], "BYE"

        new_match = await insert_one("matches", {
            "tournament_id": tid,
            "player_white_id": p1,
            "player_black_id": p2,
            "board_size": t.get("board_size", 7),
            "round_num": next_round,
            "match_index": i // 2,
            "status": "completed" if p2 == "BYE" else "scheduled",
            "white_score": 0,
            "black_score": 0,
            "winner": "white" if p2 == "BYE" else None,
            "moves": [],
            "final_board": None,
            "played_at": None,
        })
        next_match_ids.append(new_match["id"])

    if next_round < len(rounds):
        rounds[next_round] = next_match_ids
    else:
        rounds.append(next_match_ids)
    await update_one("tournaments", {"id": tid}, {"rounds": rounds})

    bye_matches = [m for m in await find_all("matches", {"tournament_id": tid, "round_num": next_round}) if m.get("player_black_id") == "BYE"]
    if bye_matches and all(m.get("status") == "completed" for m in await find_all("matches", {"tournament_id": tid, "round_num": next_round})):
        await _advance_bracket(tid, bye_matches[0])
