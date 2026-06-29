"""
Game routes — live game sessions, moves, AI, and bot-vs-bot orchestration.
"""
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

# In-memory active games
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

    insert_one("games", {
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
        raise HTTPException(404, "Game session not found. Start a new game.")
    result = game.make_move(move.row, move.col)
    if "error" in result:
        raise HTTPException(400, result["error"])

    if game.is_finished:
        _persist_finished(game_id, game)

    await asyncio.sleep(0.2)
    state = game.get_state()
    state["game_id"] = game_id
    return state


@router.post("/{game_id}/ai-move")
async def ai_move(game_id: str):
    game = active_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game session not found. Start a new game.")
    result = game.get_ai_move()
    if "error" in result:
        raise HTTPException(400, result["error"])

    if game.is_finished:
        _persist_finished(game_id, game)

    await asyncio.sleep(0.2)
    state = game.get_state()
    state["game_id"] = game_id
    return state


@router.post("/{game_id}/bot-step")
async def bot_step(game_id: str):
    """
    Make a single bot move with robust logging and retries.

    Logic:
    - Try to get a bot move up to max_attempts (3).
    - Log each failed attempt (timeout, bad response, illegal move, engine reject).
    - If all attempts fail, the current bot forfeits and opponent wins.
    - Response includes bot_step_debug describing what happened.
    """
    game = active_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game session not found. Start a new game.")
    if game.is_finished:
        state = game.get_state()
        state["game_id"] = game_id
        state["bot_step_debug"] = {
            "message": "Game already finished",
            "attempts": [],
            "max_attempts": 0,
            "forfeited": False,
        }
        return state

    # Look up which bots are playing
    game_doc = find_one("games", {"id": game_id})
    if not game_doc:
        raise HTTPException(404, "Game record not found")

    state = game.get_state()
    current_stone = state["current_player"]   # "W" or "B"

    if current_stone == "W":
        bot_id_key = "bot_white_id"
        bot_doc = find_one("bots", {"id": game_doc.get("bot_white_id", "")})
    else:
        bot_id_key = "bot_black_id"
        bot_doc = find_one("bots", {"id": game_doc.get("bot_black_id", "")})

    if not bot_doc:
        raise HTTPException(400, f"Bot not found for {'white' if current_stone == 'W' else 'black'}")

    opponent_stone = "B" if current_stone == "W" else "W"

    max_attempts = 3
    attempts_log: list[dict] = []
    successful_move: dict | None = None

    for attempt in range(1, max_attempts + 1):
        attempt_info: dict = {
            "attempt": attempt,
            "bot_id": bot_doc["id"],
            "bot_name": bot_doc["name"],
            "stone": current_stone,
        }

        # Refresh state each attempt in case something changed
        state = game.get_state()

        try:
            row, col = await _call_bot(bot_doc, state, current_stone, opponent_stone, game.n)
        except httpx.TimeoutException:
            attempt_info["error_type"] = "bot_timeout"
            attempt_info["source"] = "bot"
            attempt_info["message"] = "Bot did not respond within 5 seconds"
            attempts_log.append(attempt_info)
            continue
        except httpx.RequestError as e:
            attempt_info["error_type"] = "bot_http_error"
            attempt_info["source"] = "bot"
            attempt_info["message"] = str(e)
            attempts_log.append(attempt_info)
            continue
        except Exception as e:
            attempt_info["error_type"] = "api_unexpected_error"
            attempt_info["source"] = "api"
            attempt_info["message"] = str(e)
            attempts_log.append(attempt_info)
            continue

        # Bounds / legality checks before asking engine
        if not (0 <= row < game.n and 0 <= col < game.n):
            attempt_info["error_type"] = "bot_out_of_bounds"
            attempt_info["source"] = "bot"
            attempt_info["message"] = f"Move ({row},{col}) is out of bounds"
            attempts_log.append(attempt_info)
            continue

        if state["board"][row][col] != ".":
            attempt_info["error_type"] = "bot_illegal_move_cell_occupied"
            attempt_info["source"] = "bot"
            attempt_info["message"] = f"Move ({row},{col}) targets non-empty cell"
            attempts_log.append(attempt_info)
            continue

        # Ask engine to apply move
        result = game.make_move(row, col)
        if "error" in result:
            attempt_info["error_type"] = "engine_rejected_move"
            attempt_info["source"] = "api"
            attempt_info["message"] = result["error"]
            attempts_log.append(attempt_info)
            continue

        # Success
        attempt_info["success"] = True
        attempt_info["move"] = {"row": row, "col": col}
        attempts_log.append(attempt_info)
        successful_move = {
            "row": row,
            "col": col,
            "player": current_stone,
            "bot": bot_doc["name"],
        }
        break

    forfeited = False

    # If all attempts failed, forfeit the game for this bot
    if successful_move is None:
        forfeited = True
        # Mark game as finished with opponent as winner
        game.is_finished = True
        game.winner = "white" if opponent_stone == "W" else "black"

        # Persist results (this will also update matches / player stats)
        _persist_finished(game_id, game)

        # Update bot stats: current bot loses, opponent (if bot) wins
        final = game.get_state()
        for bid_key, role in [("bot_white_id", "white"), ("bot_black_id", "black")]:
            bid = game_doc.get(bid_key)
            if bid:
                inc = {"games_played": 1}
                if final["winner"] == role:
                    inc["wins"] = 1
                else:
                    inc["losses"] = 1
                update_inc("bots", {"id": bid}, inc)
    else:
        # Normal end-of-move processing
        if game.is_finished:
            _persist_finished(game_id, game)
            # Update bot stats for completed game
            final = game.get_state()
            for bid_key, role in [("bot_white_id", "white"), ("bot_black_id", "black")]:
                bid = game_doc.get(bid_key)
                if bid:
                    inc = {"games_played": 1}
                    if final["winner"] == role:
                        inc["wins"] = 1
                    elif final["winner"] == "draw":
                        inc["draws"] = 1
                    else:
                        inc["losses"] = 1
                    update_inc("bots", {"id": bid}, inc)

    await asyncio.sleep(0.2)
    new_state = game.get_state()
    new_state["game_id"] = game_id
    if successful_move:
        new_state["last_move"] = successful_move
    else:
        new_state["last_move"] = None
    new_state["bot_step_debug"] = {
        "attempts": attempts_log,
        "max_attempts": max_attempts,
        "forfeited": forfeited,
    }
    return new_state


@router.get("/{game_id}")
async def get_game(game_id: str):
    game = active_games.get(game_id)
    if not game:
        raise HTTPException(404, "Game session not found")
    state = game.get_state()
    state["game_id"] = game_id
    return state


# ===== Bot vs Bot =====

async def _call_bot(bot_doc: dict, game_state: dict, stone: str,
                    opponent_stone: str, board_size: int) -> tuple[int, int]:
    """
    Call a bot, which can be either:
    - HTTP bot: uses bot_doc["api_url"]
    - Local Python bot: imports module + function and calls it directly
    Returns (row, col). Falls back to random on error.
    """
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
        # Extra compatibility fields some team bots expect
        "current_player": stone,
    }

    bot_type = bot_doc.get("type", "http")

    # Local Python bot
    if bot_type == "local_py":
        module_name = bot_doc.get("module")
        fn_name = bot_doc.get("entry_function", "bot_move")
        try:
            mod = importlib.import_module(module_name)
            fn = getattr(mod, fn_name)
        except Exception:
            return _random_legal_move(game_state["board"], board_size)

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fn, payload),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            return _random_legal_move(game_state["board"], board_size)
        except Exception:
            return _random_legal_move(game_state["board"], board_size)

        try:
            return int(result["row"]), int(result["col"])
        except Exception:
            return _random_legal_move(game_state["board"], board_size)

    # HTTP bot (default)
    bot_url = bot_doc.get("api_url", "").rstrip("/")
    if not bot_url:
        return _random_legal_move(game_state["board"], board_size)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(bot_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return int(data["row"]), int(data["col"])
    except Exception:
        # Fallback: pick a random legal move
        return _random_legal_move(game_state["board"], board_size)


def _random_legal_move(board: list, board_size: int) -> tuple[int, int]:
    """Pick a random empty cell."""
    empty = []
    for r in range(board_size):
        for c in range(board_size):
            if board[r][c] == ".":
                empty.append((r, c))
    if empty:
        return random.choice(empty)
    return (0, 0)


@router.post("/bot-game/run")
async def run_bot_game(
    board_size: int = 7,
    bot_white_id: str = "",
    bot_black_id: str = "",
    match_id: str = None,
):
    """Run a complete bot-vs-bot game. Both bots play automatically."""
    bot_w = find_one("bots", {"id": bot_white_id})
    bot_b = find_one("bots", {"id": bot_black_id})
    if not bot_w:
        raise HTTPException(404, f"White bot not found: {bot_white_id}")
    if not bot_b:
        raise HTTPException(404, f"Black bot not found: {bot_black_id}")

    game = PahTumGame(
        board_size_n=board_size,
        mode="bot_vs_bot",
        player_white=bot_w["name"],
        player_black=bot_b["name"],
    )
    game_id = uuid.uuid4().hex[:16]

    insert_one("games", {
        "id": game_id,
        "match_id": match_id,
        "board_size": board_size,
        "mode": "bot_vs_bot",
        "player_white": bot_w["name"],
        "player_black": bot_b["name"],
        "bot_white_id": bot_white_id,
        "bot_black_id": bot_black_id,
        "is_finished": False,
    })

    # Record each move for the replay
    all_moves = []
    board_snapshots = []
    max_turns = board_size * board_size  # hard safety limit

    for turn_num in range(max_turns):
        if game.is_finished:
            break

        state = game.get_state()
        current_stone = state["current_player"]  # "W" or "B"

        if current_stone == "W":
            bot_doc = bot_w
        else:
            bot_doc = bot_b

        row, col = await _call_bot(bot_doc, state, current_stone,
                                    "B" if current_stone == "W" else "W", board_size)

        result = game.make_move(row, col)
        if "error" in result:
            # Bot made invalid move — use random fallback
            row, col = _random_legal_move(state["board"], board_size)
            result = game.make_move(row, col)
            if "error" in result:
                break  # Board full or something unexpected

        all_moves.append({
            "row": row, "col": col, "player": current_stone,
            "bot": bot_w["name"] if current_stone == "W" else bot_b["name"],
        })
        current_state = game.get_state()
        board_snapshots.append({
            "board": [r[:] for r in current_state["board"]],
            "white_score": current_state["white_score"],
            "black_score": current_state["black_score"],
        })

    # Final state
    final = game.get_state()

    # Update game record
    update_one("games", {"id": game_id}, {
        "is_finished": True,
        "board": final["board"],
        "moves": all_moves,
        "white_score": final["white_score"],
        "black_score": final["black_score"],
        "winner": final["winner"],
    })

    # Update bot stats
    for bot_doc, role in [(bot_w, "white"), (bot_b, "black")]:
        inc = {"games_played": 1}
        if final["winner"] == role:
            inc["wins"] = 1
        elif final["winner"] == "draw":
            inc["draws"] = 1
        else:
            inc["losses"] = 1
        update_inc("bots", {"id": bot_doc["id"]}, inc)

    # Persist to match if linked
    if match_id:
        _persist_match_result(match_id, final)

    return {
        "game_id": game_id,
        "winner": final["winner"],
        "white_score": final["white_score"],
        "black_score": final["black_score"],
        "total_moves": len(all_moves),
        "moves": all_moves,
        "board_snapshots": board_snapshots,
        "final_board": final["board"],
        "bot_white": bot_w["name"],
        "bot_black": bot_b["name"],
    }


def _persist_match_result(match_id: str, state: dict):
    update_one("matches", {"id": match_id}, {
        "status": "completed",
        "white_score": state["white_score"],
        "black_score": state["black_score"],
        "winner": state["winner"],
        "moves": state["moves"],
        "final_board": state["board"],
        "played_at": datetime.now(timezone.utc).isoformat(),
    })


def _persist_finished(game_id: str, game: PahTumGame):
    state = game.get_state()
    update_one("games", {"id": game_id}, {
        "is_finished": True,
        "board": state["board"],
        "moves": state["moves"],
        "white_score": state["white_score"],
        "black_score": state["black_score"],
        "winner": state["winner"],
    })
    game_doc = find_one("games", {"id": game_id})
    if game_doc and game_doc.get("match_id"):
        _persist_match_result(game_doc["match_id"], state)
        match = find_one("matches", {"id": game_doc["match_id"]})
        if match:
            for pid_key, score_key, role in [
                ("player_white_id", "white_score", "white"),
                ("player_black_id", "black_score", "black"),
            ]:
                pid = match.get(pid_key)
                if pid and pid != "AI":
                    inc = {"matches_played": 1, "total_score": match.get(score_key, 0)}
                    if state["winner"] == role:
                        inc["wins"] = 1
                    elif state["winner"] == "draw":
                        inc["draws"] = 1
                    else:
                        inc["losses"] = 1
                    update_inc("players", {"id": pid}, inc)
