from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from database import find_one, insert_one, update_one, update_inc
from models import GameCreate, MoveRequest
from game_engine import PahTumGame
import httpx
import uuid
import random
import importlib
import asyncio

router = APIRouter(prefix="/api/game", tags=["game"])
active_games: dict[str, PahTumGame] = {}

@router.post("/new")
async def new_game(g: GameCreate):
    game = PahTumGame(
        board_size_n=g.board_size,
        mode=g.mode,
        player_white=g.player_white,
        player_black=g.player_black,
    )
    game_id = uuid.uuid4().hex[:16]
    active_games[game_id] = game

    await insert_one("games", {
        "id": game_id,
        "match_id": g.match_id,
        "board_size": g.board_size,
        "mode": g.mode,
        "player_white": g.player_white,
        "player_black": g.player_black,
        "bot_white_id": g.bot_white_id,
        "bot_black_id": g.bot_black_id,
        "is_finished": False,
    })

    state = game.get_state()
    state["game_id"] = game_id
    return state

@router.post("/{game_id}/move")
async def make_move(game_id: str, move: MoveRequest):
    game = active_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    result = game.make_move(move.row, move.col)
    if "error" in result: raise HTTPException(400, result["error"])

    if game.is_finished:
        await _persist_finished(game_id, game)

    await asyncio.sleep(0.2)
    state = game.get_state()
    state["game_id"] = game_id
    return state

@router.post("/{game_id}/ai-move")
async def ai_move(game_id: str):
    game = active_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    result = game.get_ai_move()
    if "error" in result: raise HTTPException(400, result["error"])

    if game.is_finished:
        await _persist_finished(game_id, game)

    await asyncio.sleep(0.2)
    state = game.get_state()
    state["game_id"] = game_id
    return state

@router.post("/{game_id}/bot-step")
async def bot_step(game_id: str):
    game = active_games.get(game_id)
    if not game: raise HTTPException(404, "Game not found")
    if game.is_finished:
        state = game.get_state()
        state["game_id"] = game_id
        return state

    game_doc = await find_one("games", {"id": game_id})
    if not game_doc: raise HTTPException(404, "Game record not found")

    state = game.get_state()
    current_stone = state["current_player"]

    if current_stone == "W":
        bot_doc = await find_one("bots", {"id": game_doc.get("bot_white_id", "")})
    else:
        bot_doc = await find_one("bots", {"id": game_doc.get("bot_black_id", "")})

    if not bot_doc: raise HTTPException(400, "Bot not found")
    opponent_stone = "B" if current_stone == "W" else "W"

    try:
        row, col = await _call_bot(bot_doc, state, current_stone, opponent_stone, game.n)
    except Exception as e:
        row, col = _random_legal_move(state["board"], game.n)

    result = game.make_move(row, col)
    if "error" in result:
        row, col = _random_legal_move(state["board"], game.n)
        game.make_move(row, col)

    if game.is_finished:
        await _persist_finished(game_id, game)
        final = game.get_state()
        for bid_key, role in [("bot_white_id", "white"), ("bot_black_id", "black")]:
            bid = game_doc.get(bid_key)
            if bid:
                inc = {"games_played": 1}
                if final["winner"] == role: inc["wins"] = 1
                elif final["winner"] == "draw": inc["draws"] = 1
                else: inc["losses"] = 1
                await update_inc("bots", {"id": bid}, inc)

    await asyncio.sleep(0.2)
    new_state = game.get_state()
    new_state["game_id"] = game_id
    new_state["last_move"] = {"row": row, "col": col}
    return new_state

@router.get("/{game_id}")
async def get_game(game_id: str):
    game = active_games.get(game_id)
    if not game: raise HTTPException(404, "Game not found")
    state = game.get_state()
    state["game_id"] = game_id
    return state

async def _call_bot(bot_doc: dict, game_state: dict, stone: str, opponent_stone: str, board_size: int):
    payload = {
        "board": game_state["board"],
        "board_size": board_size,
        "your_stone": stone,
        "opponent_stone": opponent_stone,
        "scores_for_n": game_state.get("scores_for_n", {}),
        "your_score": game_state["white_score"] if stone == "W" else game_state["black_score"],
        "opponent_score": game_state["black_score"] if stone == "W" else game_state["white_score"],
        "turn": game_state["turn"],
        "moves_history": game_state.get("moves", []),
        "current_player": stone,
    }

    if bot_doc.get("type") == "local_py":
        mod = importlib.import_module(bot_doc.get("module"))
        fn = getattr(mod, bot_doc.get("entry_function", "bot_move"))
        loop = asyncio.get_event_loop()
        res = await asyncio.wait_for(loop.run_in_executor(None, fn, payload), timeout=5.0)
        return int(res["row"]), int(res["col"])

    bot_url = bot_doc.get("api_url", "").rstrip("/")
    if not bot_url: return _random_legal_move(game_state["board"], board_size)
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(bot_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return int(data["row"]), int(data["col"])

def _random_legal_move(board: list, board_size: int):
    empty = [(r, c) for r in range(board_size) for c in range(board_size) if board[r][c] == "."]
    return random.choice(empty) if empty else (0, 0)

@router.post("/bot-game/run")
async def run_bot_game(board_size: int = 7, bot_white_id: str = "", bot_black_id: str = "", match_id: str = None):
    bot_w = await find_one("bots", {"id": bot_white_id})
    bot_b = await find_one("bots", {"id": bot_black_id})
    if not bot_w or not bot_b: raise HTTPException(404, "Bot not found")

    game = PahTumGame(board_size_n=board_size, mode="bot_vs_bot", player_white=bot_w["name"], player_black=bot_b["name"])
    game_id = uuid.uuid4().hex[:16]
    await insert_one("games", {
        "id": game_id, "match_id": match_id, "board_size": board_size, "mode": "bot_vs_bot",
        "player_white": bot_w["name"], "player_black": bot_b["name"],
        "bot_white_id": bot_white_id, "bot_black_id": bot_black_id, "is_finished": False,
    })

    all_moves = []
    board_snapshots = []
    for _ in range(board_size * board_size):
        if game.is_finished: break
        state = game.get_state()
        c_stone = state["current_player"]
        bot_doc = bot_w if c_stone == "W" else bot_b
        
        try:
            row, col = await _call_bot(bot_doc, state, c_stone, "B" if c_stone == "W" else "W", board_size)
        except:
            row, col = _random_legal_move(state["board"], board_size)
            
        res = game.make_move(row, col)
        if "error" in res:
            row, col = _random_legal_move(state["board"], board_size)
            game.make_move(row, col)
            
        all_moves.append({"row": row, "col": col, "player": c_stone, "bot": bot_w["name"] if c_stone == "W" else bot_b["name"]})
        cs = game.get_state()
        board_snapshots.append({"board": [r[:] for r in cs["board"]], "white_score": cs["white_score"], "black_score": cs["black_score"]})

    final = game.get_state()
    await update_one("games", {"id": game_id}, {
        "is_finished": True, "board": final["board"], "moves": all_moves,
        "white_score": final["white_score"], "black_score": final["black_score"], "winner": final["winner"]
    })

    for bot_doc, role in [(bot_w, "white"), (bot_b, "black")]:
        inc = {"games_played": 1}
        if final["winner"] == role: inc["wins"] = 1
        elif final["winner"] == "draw": inc["draws"] = 1
        else: inc["losses"] = 1
        await update_inc("bots", {"id": bot_doc["id"]}, inc)

    if match_id:
        await _persist_match_result(match_id, final)

    return {
        "game_id": game_id, "winner": final["winner"], "white_score": final["white_score"], "black_score": final["black_score"],
        "total_moves": len(all_moves), "moves": all_moves, "board_snapshots": board_snapshots, "final_board": final["board"],
        "bot_white": bot_w["name"], "bot_black": bot_b["name"]
    }

async def _persist_match_result(match_id: str, state: dict):
    await update_one("matches", {"id": match_id}, {
        "status": "completed", "white_score": state["white_score"], "black_score": state["black_score"],
        "winner": state["winner"], "moves": state["moves"], "final_board": state["board"],
        "played_at": datetime.now(timezone.utc).isoformat(),
    })

async def _persist_finished(game_id: str, game: PahTumGame):
    state = game.get_state()
    await update_one("games", {"id": game_id}, {
        "is_finished": True, "board": state["board"], "moves": state["moves"],
        "white_score": state["white_score"], "black_score": state["black_score"], "winner": state["winner"]
    })
    game_doc = await find_one("games", {"id": game_id})
    if game_doc and game_doc.get("match_id"):
        await _persist_match_result(game_doc["match_id"], state)
        match = await find_one("matches", {"id": game_doc["match_id"]})
        if match:
            for pid_key, score_key, role in [("player_white_id", "white_score", "white"), ("player_black_id", "black_score", "black")]:
                pid = match.get(pid_key)
                if pid and pid != "AI":
                    inc = {"matches_played": 1, "total_score": match.get(score_key, 0)}
                    if state["winner"] == role: inc["wins"] = 1
                    elif state["winner"] == "draw": inc["draws"] = 1
                    else: inc["losses"] = 1
                    await update_inc("users", {"id": pid}, inc)
