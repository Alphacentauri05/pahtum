from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
import httpx
import importlib
import asyncio
from pathlib import Path
import re
import uuid
from database import find_all, find_one, insert_one, update_one, delete_one
from models import BotCreate
import auth

router = APIRouter(prefix="/api/bots", tags=["bots"])

TEAM_BOTS_DIR = Path(__file__).parent.parent / "team_bots"
TEAM_BOTS_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_STATE = {
    "board": [[".", ".", ".", ".", ".", ".", "."],
              [".", ".", ".", ".", ".", ".", "."],
              [".", ".", ".", ".", ".", ".", "."],
              [".", ".", ".", "W", ".", ".", "."],
              [".", ".", ".", ".", ".", ".", "."],
              [".", ".", ".", ".", ".", "B", "."],
              [".", ".", ".", ".", ".", ".", "."]],
    "board_size": 7,
    "your_stone": "W",
    "opponent_stone": "B",
    "scores_for_n": {"1": 0, "2": 0, "3": 3, "4": 10, "5": 25, "6": 56, "7": 119},
    "your_score": 0,
    "opponent_score": 0,
    "turn": 2,
    "moves_history": [{"row": 3, "col": 3, "player": "W"}, {"row": 5, "col": 5, "player": "B"}],
    "current_player": "W",
}

@router.post("")
async def register_bot(b: BotCreate, current_user: dict = Depends(auth.get_current_user)):
    existing = await find_one("bots", {"name": b.name, "owner_id": current_user["id"]})
    if existing:
        raise HTTPException(400, "You already have a bot with this name")
        
    doc = await insert_one("bots", {
        "name": b.name,
        "owner_id": current_user["id"],
        "description": b.description,
        "active": True,
        "type": "http", # Or adjust to local
        "api_url": "", # Deprecated maybe, but keeping for compatibility
        "status": "registered",
        "wins": 0, "losses": 0, "draws": 0, "games_played": 0,
    })
    return doc

@router.post("/upload-local")
async def upload_local_bot(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    entry_function: str = Form("bot_move"),
    current_user: dict = Depends(auth.get_current_user)
):
    if not file.filename.endswith(".py"):
        raise HTTPException(400, "Only .py files are allowed")

    existing = await find_one("bots", {"name": name, "owner_id": current_user["id"]})
    if existing:
        raise HTTPException(400, "You already have a bot with this name")

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
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, entry_function)
        if not callable(fn): raise Exception("Not callable")
    except Exception as e:
        raise HTTPException(400, f"Could not import {module_path}.{entry_function}: {e}")

    doc = await insert_one("bots", {
        "name": name,
        "owner_id": current_user["id"],
        "description": description,
        "type": "local_py",
        "module": module_path,
        "entry_function": entry_function,
        "status": "registered",
        "active": True,
        "wins": 0, "losses": 0, "draws": 0, "games_played": 0,
    })
    return doc

from pydantic import BaseModel
class InlineBotCreate(BaseModel):
    name: str
    owner: str = ""
    description: str = ""
    code: str
    entry_function: str = "bot_move"

@router.post("/inline")
async def upload_inline_bot(
    data: InlineBotCreate,
    current_user: dict = Depends(auth.get_current_user)
):
    existing = await find_one("bots", {"name": data.name, "owner_id": current_user["id"]})
    if existing:
        raise HTTPException(400, "You already have a bot with this name")

    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", data.name).strip("_").lower() or "bot"
    suffix = uuid.uuid4().hex[:8]
    module_basename = f"{slug}_{suffix}"
    target_path = TEAM_BOTS_DIR / f"{module_basename}.py"

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(data.code)
    except Exception as e:
        raise HTTPException(500, f"Failed to save bot file: {e}")

    module_path = f"team_bots.{module_basename}"
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, data.entry_function)
        if not callable(fn): raise Exception("Not callable")
    except Exception as e:
        raise HTTPException(400, f"Could not import {module_path}.{data.entry_function}: {e}")

    doc = await insert_one("bots", {
        "name": data.name,
        "owner_id": current_user["id"],
        "description": data.description,
        "type": "local_py",
        "module": module_path,
        "entry_function": data.entry_function,
        "status": "registered",
        "active": True,
        "wins": 0, "losses": 0, "draws": 0, "games_played": 0,
    })
    return doc

@router.get("")
async def list_my_bots(current_user: dict = Depends(auth.get_current_user)):
    return await find_all("bots", {"owner_id": current_user["id"]}, sort_key="created_at", sort_reverse=True)

@router.get("/all")
async def list_all_bots(admin: dict = Depends(auth.get_admin_user)):
    return await find_all("bots", sort_key="created_at", sort_reverse=True)

@router.get("/{bot_id}")
async def get_bot(bot_id: str, current_user: dict = Depends(auth.get_current_user)):
    doc = await find_one("bots", {"id": bot_id})
    if not doc: raise HTTPException(404, "Bot not found")
    if doc.get("owner_id") != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You do not own this bot")
    return doc

@router.put("/{bot_id}")
async def update_bot(bot_id: str, b: BotCreate, current_user: dict = Depends(auth.get_current_user)):
    bot = await find_one("bots", {"id": bot_id})
    if not bot: raise HTTPException(404, "Bot not found")
    if bot.get("owner_id") != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You do not own this bot")
        
    await update_one("bots", {"id": bot_id}, {
        "name": b.name,
        "description": b.description,
    })
    return {"success": True}

@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, current_user: dict = Depends(auth.get_current_user)):
    bot = await find_one("bots", {"id": bot_id})
    if not bot: raise HTTPException(404, "Bot not found")
    if bot.get("owner_id") != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You do not own this bot")
        
    await delete_one("bots", {"id": bot_id})
    return {"success": True}

@router.post("/{bot_id}/test")
async def test_bot(bot_id: str, current_user: dict = Depends(auth.get_current_user)):
    bot = await find_one("bots", {"id": bot_id})
    if not bot: raise HTTPException(404, "Bot not found")
    if bot.get("owner_id") != current_user["id"] and current_user.get("role") != "ADMIN":
        raise HTTPException(403, "You do not own this bot")

    if bot.get("type") == "local_py":
        module_name = bot.get("module")
        fn_name = bot.get("entry_function", "bot_move")
        try:
            mod = importlib.import_module(module_name)
            fn = getattr(mod, fn_name)
        except Exception as e:
            await update_one("bots", {"id": bot_id}, {"status": "error"})
            return {"success": False, "status": "import_error", "message": str(e)}

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(loop.run_in_executor(None, fn, SAMPLE_STATE), timeout=5.0)
        except asyncio.TimeoutError:
            await update_one("bots", {"id": bot_id}, {"status": "timeout"})
            return {"success": False, "status": "timeout", "message": "Bot timeout"}
        except Exception as e:
            await update_one("bots", {"id": bot_id}, {"status": "error"})
            return {"success": False, "status": "error", "message": str(e)}
        data = result or {}
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(bot["api_url"], json=SAMPLE_STATE)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            await update_one("bots", {"id": bot_id}, {"status": "error"})
            return {"success": False, "status": "error", "message": str(e)}

    if "row" not in data or "col" not in data:
        return {"success": False, "status": "invalid_response", "message": "Missing row/col"}
        
    await update_one("bots", {"id": bot_id}, {"status": "online"})
    return {"success": True, "status": "online", "move": {"row": data["row"], "col": data["col"]}}
