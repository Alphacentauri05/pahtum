"""
Bot routes — registration, listing, testing, editing, deletion.
Supports:
- HTTP bots (external URL implementing the PlayerAPI contract)
- Local Python bots (module + function on the same server)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import httpx
import importlib
import asyncio
from pathlib import Path
import re
import uuid
from database import find_all, find_one, insert_one, update_one, delete_one
from models import BotCreate, LocalBotCreate

router = APIRouter(prefix="/api/bots", tags=["bots"])

TEAM_BOTS_DIR = Path(__file__).parent.parent / "team_bots"
TEAM_BOTS_DIR.mkdir(parents=True, exist_ok=True)

# Sample game state for testing bots
SAMPLE_STATE = {
    "board": [
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", "W", ".", ".", "."],
        [".", ".", ".", ".", ".", ".", "."],
        [".", ".", ".", ".", ".", "B", "."],
        [".", ".", ".", ".", ".", ".", "."],
    ],
    "board_size": 7,
    "your_stone": "W",
    "opponent_stone": "B",
    "scores_for_n": {"1": 0, "2": 0, "3": 3, "4": 10, "5": 25, "6": 56, "7": 119},
    "your_score": 0,
    "opponent_score": 0,
    "turn": 2,
    "moves_history": [
        {"row": 3, "col": 3, "player": "W"},
        {"row": 5, "col": 5, "player": "B"},
    ],
    # Extra fields some team bots expect (to avoid KeyError in tests)
    "current_player": "W",
}


@router.post("")
async def register_bot(b: BotCreate):
    existing = find_one("bots", {"name": b.name})
    if existing:
        raise HTTPException(400, "A bot with this name already exists")
    doc = insert_one("bots", {
        "name": b.name,
        "api_url": b.api_url.rstrip("/"),
        "owner": b.owner,
        "description": b.description,
        "type": "http",
        "status": "registered",
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "games_played": 0,
    })
    return doc


@router.post("/local")
async def register_local_bot(b: LocalBotCreate):
    """
    Register a local Python bot that lives as a .py module on the server.

    Teams provide:
    - module: import path, e.g. "team7" or "team_bots.team7_algo1"
    - entry_function: callable inside that module, e.g. "bot_move"
    """
    existing = find_one("bots", {"name": b.name})
    if existing:
        raise HTTPException(400, "A bot with this name already exists")

    # Validate that we can import and call the function
    try:
        mod = importlib.import_module(b.module)
        fn = getattr(mod, b.entry_function)
    except Exception as e:
        raise HTTPException(400, f"Could not import {b.module}.{b.entry_function}: {e}")

    if not callable(fn):
        raise HTTPException(400, f"{b.module}.{b.entry_function} is not callable")

    doc = insert_one("bots", {
        "name": b.name,
        "owner": b.owner,
        "description": b.description,
        "type": "local_py",
        "module": b.module,
        "entry_function": b.entry_function,
        "status": "registered",
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "games_played": 0,
    })
    return doc


@router.post("/upload-local")
async def upload_local_bot(
    file: UploadFile = File(...),
    name: str = Form(...),
    owner: str = Form(""),
    description: str = Form(""),
    entry_function: str = Form("bot_move"),
):
    """
    Upload a single .py file and register it as a local Python bot.

    The file is saved under backend/team_bots/, imported as a module, and the
    specified entry_function (default "bot_move") is used as the bot entrypoint.
    """
    if not file.filename.endswith(".py"):
        raise HTTPException(400, "Only .py files are allowed")

    existing = find_one("bots", {"name": name})
    if existing:
        raise HTTPException(400, "A bot with this name already exists")

    # Create a safe module name based on bot name and a short random suffix
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower() or "bot"
    suffix = uuid.uuid4().hex[:8]
    module_basename = f"{slug}_{suffix}"
    target_path = TEAM_BOTS_DIR / f"{module_basename}.py"

    content = await file.read()
    try:
        with open(target_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"Failed to save bot file: {e}")

    module_path = f"team_bots.{module_basename}"

    # Validate import and function
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, entry_function)
    except Exception as e:
        raise HTTPException(400, f"Could not import {module_path}.{entry_function}: {e}")

    if not callable(fn):
        raise HTTPException(400, f"{module_path}.{entry_function} is not callable")

    doc = insert_one("bots", {
        "name": name,
        "owner": owner,
        "description": description,
        "type": "local_py",
        "module": module_path,
        "entry_function": entry_function,
        "status": "registered",
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "games_played": 0,
    })
    return doc


@router.get("")
async def list_bots():
    return find_all("bots", sort_key="wins", sort_reverse=True)


@router.get("/{bot_id}")
async def get_bot(bot_id: str):
    doc = find_one("bots", {"id": bot_id})
    if not doc:
        raise HTTPException(404, "Bot not found")
    return doc


@router.put("/{bot_id}")
async def update_bot(bot_id: str, b: BotCreate):
    bot = find_one("bots", {"id": bot_id})
    if not bot:
        raise HTTPException(404, "Bot not found")
    update: dict = {
        "name": b.name,
        "owner": b.owner,
        "description": b.description,
    }
    if bot.get("type", "http") == "http":
        update["api_url"] = b.api_url.rstrip("/")
    update_one("bots", {"id": bot_id}, update)
    return {"success": True}


@router.post("/{bot_id}/test")
async def test_bot(bot_id: str):
    """Test a bot by sending a sample game state and checking the response."""
    bot = find_one("bots", {"id": bot_id})
    if not bot:
        raise HTTPException(404, "Bot not found")

    # Local Python bot: import and call function directly (with timeout)
    if bot.get("type") == "local_py":
        module_name = bot.get("module")
        fn_name = bot.get("entry_function", "bot_move")
        try:
            mod = importlib.import_module(module_name)
            fn = getattr(mod, fn_name)
        except Exception as e:
            update_one("bots", {"id": bot_id}, {"status": "error"})
            return {
                "success": False,
                "status": "import_error",
                "message": f"Could not import {module_name}.{fn_name}: {e}",
            }

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, fn, SAMPLE_STATE),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            update_one("bots", {"id": bot_id}, {"status": "timeout"})
            return {"success": False, "status": "timeout", "message": "Bot did not respond within 5 seconds"}
        except Exception as e:
            update_one("bots", {"id": bot_id}, {"status": "error"})
            return {"success": False, "status": "error", "message": str(e)}

        data = result or {}
    else:
        # HTTP bot — existing behavior
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(bot["api_url"], json=SAMPLE_STATE)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            update_one("bots", {"id": bot_id}, {"status": "timeout"})
            return {"success": False, "status": "timeout", "message": "Bot did not respond within 5 seconds"}
        except httpx.ConnectError:
            update_one("bots", {"id": bot_id}, {"status": "offline"})
            return {"success": False, "status": "offline", "message": f"Could not connect to {bot['api_url']}"}
        except Exception as e:
            update_one("bots", {"id": bot_id}, {"status": "error"})
            return {"success": False, "status": "error", "message": str(e)}

    # Common validation for both HTTP and local bots
    if "row" not in data or "col" not in data:
        return {
            "success": False,
            "status": "invalid_response",
            "message": f"Bot responded but missing row/col. Got: {data}",
        }

    row, col = int(data["row"]), int(data["col"])
    n = SAMPLE_STATE["board_size"]
    if not (0 <= row < n and 0 <= col < n):
        return {
            "success": False,
            "status": "out_of_bounds",
            "message": f"Bot returned ({row},{col}) which is out of bounds for {n}×{n}",
        }

    update_one("bots", {"id": bot_id}, {"status": "online"})
    return {
        "success": True,
        "status": "online",
        "message": f"Bot responded with move ({row},{col}) ✓",
        "move": {"row": row, "col": col},
    }


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str):
    ok = delete_one("bots", {"id": bot_id})
    if not ok:
        raise HTTPException(404, "Bot not found")
    return {"success": True}
