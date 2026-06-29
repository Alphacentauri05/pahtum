"""
Match routes — scheduling and results, with tournament auto-advance.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from database import find_all, find_one, insert_one, update_one, update_inc
from models import MatchCreate

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.post("")
async def create_match(m: MatchCreate):
    doc = insert_one("matches", {
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
    results = find_all("matches", query if query else None, sort_key="created_at", sort_reverse=True, limit=limit)
    for m in results:
        for key in ["player_white_id", "player_black_id"]:
            pid = m.get(key)
            name_key = key.replace("_id", "_name")
            if pid and pid != "AI" and pid != "BYE":
                p = find_one("players", {"id": pid})
                m[name_key] = p["name"] if p else "Unknown"
            elif pid == "BYE":
                m[name_key] = "BYE"
            else:
                m[name_key] = "AI Bot"
    return results


@router.get("/{mid}")
async def get_match(mid: str):
    doc = find_one("matches", {"id": mid})
    if not doc:
        raise HTTPException(404, "Match not found")
    return doc


@router.put("/{mid}/result")
async def update_match_result(mid: str, white_score: int, black_score: int,
                               winner: str, moves: list = None, final_board: list = None):
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

    ok = update_one("matches", {"id": mid}, upd)
    if not ok:
        raise HTTPException(404, "Match not found")

    match = find_one("matches", {"id": mid})
    if match:
        # Update player stats (skip bots — they track stats separately)
        for pid_key, score_key, role in [
            ("player_white_id", "white_score", "white"),
            ("player_black_id", "black_score", "black"),
        ]:
            pid = match.get(pid_key)
            if pid and pid not in ("AI", "BYE") and not pid.startswith("bot:"):
                inc = {"matches_played": 1, "total_score": match.get(score_key, 0)}
                if winner == role:
                    inc["wins"] = 1
                elif winner == "draw":
                    inc["draws"] = 1
                else:
                    inc["losses"] = 1
                update_inc("players", {"id": pid}, inc)

        # Auto-advance tournament
        if match.get("tournament_id"):
            t = find_one("tournaments", {"id": match["tournament_id"]})
            if t and t.get("format") == "group_stage":
                # Group stage: check if phase 2 is done → complete tournament
                phase = match.get("phase", 1)
                if phase == 2:
                    p2_matches = find_all("matches", {
                        "tournament_id": match["tournament_id"],
                        "phase": 2,
                    })
                    if all(m.get("status") == "completed" for m in p2_matches):
                        update_one("tournaments", {"id": match["tournament_id"]}, {
                            "status": "completed",
                            "phase2_status": "done",
                        })
            elif t and t.get("format", "knockout") == "knockout":
                _advance_bracket(match["tournament_id"], match)

    return {"success": True}


def _advance_bracket(tid: str, completed_match: dict):
    """After a match completes, check if the round is done and create next-round matches."""
    t = find_one("tournaments", {"id": tid})
    if not t or t.get("status") == "completed":
        return

    rounds = t.get("rounds", [])
    round_num = completed_match.get("round_num", 0)

    # Find all matches in this round
    round_matches = find_all("matches", {
        "tournament_id": tid,
        "round_num": round_num,
    })

    # Check if all matches in this round are completed
    all_done = all(m.get("status") == "completed" for m in round_matches)
    if not all_done:
        return

    # If this is the final round, complete the tournament
    total_rounds = len(rounds)
    if round_num >= total_rounds - 1:
        update_one("tournaments", {"id": tid}, {"status": "completed"})
        return

    # Collect winners from this round, sorted by match_index
    round_matches.sort(key=lambda m: m.get("match_index", 0))
    winners = []
    for m in round_matches:
        if m["winner"] == "white":
            winners.append(m["player_white_id"])
        elif m["winner"] == "black":
            winners.append(m["player_black_id"])
        else:
            # Draw: white advances (tiebreak rule)
            winners.append(m["player_white_id"])

    # Create next round matches
    next_round = round_num + 1
    next_match_ids = []
    for i in range(0, len(winners), 2):
        if i + 1 < len(winners):
            p1, p2 = winners[i], winners[i + 1]
        else:
            # Odd number: bye
            p1, p2 = winners[i], "BYE"

        new_match = insert_one("matches", {
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

    # Update rounds array in tournament
    if next_round < len(rounds):
        rounds[next_round] = next_match_ids
    else:
        rounds.append(next_match_ids)
    update_one("tournaments", {"id": tid}, {"rounds": rounds})

    # If any bye matches were auto-completed, re-check advancement
    bye_matches = [m for m in find_all("matches", {"tournament_id": tid, "round_num": next_round}) if m.get("player_black_id") == "BYE"]
    if bye_matches and all(m.get("status") == "completed" for m in find_all("matches", {"tournament_id": tid, "round_num": next_round})):
        # All next round matches are done (all byes), advance again
        _advance_bracket(tid, bye_matches[0])
