"""
Player API contract & sandbox endpoints for external bots/agents.

These endpoints are specifically for Player teams integrating their own
HTTP services. They expose:
- The canonical request/response contract.
- A sample game state payload.
- A lightweight test endpoint to validate a bot URL without registering it.
"""
from fastapi import APIRouter, HTTPException
import httpx

from database import find_one

router = APIRouter(prefix="/api/player-api", tags=["player-api"])


# Sample state mirrors what the tournament server sends to bots.
# This is intentionally small but fully representative.
SAMPLE_STATE = {
    "board": [
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", "W", ".", ".", "."],
        [".", ".", ".", ".", "B", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
    ],
    "board_size": 7,
    "your_stone": "W",
    "opponent_stone": "B",
    "scores_for_n": {"1": 0, "2": 0, "3": 3, "4": 10, "5": 25, "6": 62, "7": 141},
    "your_score": 0,
    "opponent_score": 0,
    "turn": 4,
    "moves_history": [
        {"row": 2, "col": 3, "player": "W"},
        {"row": 3, "col": 4, "player": "B"},
    ],
}


@router.get("/contract")
async def get_player_api_contract():
    """
    Describe the Player API contract that external bots must implement.

    This is a machine-readable summary that other teams can also surface
    in their own tooling or docs.
    """
    return {
        "request": {
            "method": "POST",
            "content_type": "application/json",
            "body": {
                "board": "2D array of strings '.' | 'W' | 'B', size board_size x board_size",
                "board_size": "int, typically 7",
                "your_stone": "'W' or 'B'",
                "opponent_stone": "'B' or 'W'",
                "scores_for_n": "object mapping run length (as string) to score, e.g. {'3': 3, '4': 10, ...}",
                "your_score": "int, current score for your_stone",
                "opponent_score": "int, current score for opponent_stone",
                "turn": "int, number of moves already played",
                "moves_history": "array of {row:int, col:int, player:'W'|'B'} in play order",
            },
            "timeout_seconds": 5,
        },
        "response": {
            "status": "HTTP 200 on success",
            "body": {
                "row": "int, 0-based row index of chosen move",
                "col": "int, 0-based column index of chosen move",
            },
        },
        "notes": [
            "Bots MUST respond within 5 seconds; otherwise the engine will fall back to a random legal move.",
            "Returned (row, col) must be within [0, board_size-1] and on an empty cell ('.').",
            "Board is always square and currently 7x7 for tournaments, but the contract supports other sizes.",
        ],
    }


@router.get("/sample-state")
async def get_sample_state():
    """Return a concrete sample game_state payload that will be sent to bots."""
    return SAMPLE_STATE


@router.post("/test")
async def test_player_bot(api_url: str):
    """
    One-off sandbox test for a Player bot.

    This does NOT require the bot to be registered in the system.
    It simply POSTs SAMPLE_STATE to the given URL and validates the basic
    shape and bounds of the response.
    """
    url = api_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=SAMPLE_STATE)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(408, "Bot did not respond within 5 seconds")
    except httpx.ConnectError:
        raise HTTPException(400, f"Could not connect to {url}")
    except Exception as e:
        raise HTTPException(400, f"Error calling bot: {e}")

    if "row" not in data or "col" not in data:
        raise HTTPException(400, f"Bot responded but missing row/col. Got: {data}")

    try:
        row = int(data["row"])
        col = int(data["col"])
    except Exception:
        raise HTTPException(400, f"row/col must be integers. Got: {data}")

    n = SAMPLE_STATE["board_size"]
    if not (0 <= row < n and 0 <= col < n):
        raise HTTPException(
            400,
            f"Bot returned ({row},{col}) which is out of bounds for {n}x{n}",
        )

    if SAMPLE_STATE["board"][row][col] != ".":
        raise HTTPException(
            400,
            f"Bot returned ({row},{col}) which is not an empty cell in the sample state",
        )

    return {
        "success": True,
        "status": "ok",
        "message": f"Bot responded with move ({row},{col}) ✓",
        "move": {"row": row, "col": col},
        "tested_url": url,
    }

