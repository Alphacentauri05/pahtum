from fastapi import APIRouter, HTTPException, Depends
from database import find_all, find_one, update_one, delete_one
from models import UserCreate, Role
import auth

router = APIRouter(prefix="/api/players", tags=["users"])

@router.get("")
async def list_users():
    return await find_all("users", sort_key="total_score", sort_reverse=True)

@router.get("/{uid}")
async def get_user_profile(uid: str):
    doc = await find_one("users", {"id": uid})
    if not doc: raise HTTPException(404, "User not found")
    
    # Hide password hash
    doc.pop("password_hash", None)
    
    doc["recent_matches"] = await find_all("matches", {
        "$or": [{"player_white_id": uid}, {"player_black_id": uid}]
    }, sort_key="created_at", sort_reverse=True, limit=10)
    return doc

@router.put("/{uid}")
async def update_user(uid: str, u: UserCreate, current_user: dict = Depends(auth.get_current_user)):
    if current_user["id"] != uid and current_user["role"] != Role.ADMIN:
        raise HTTPException(403, "Not authorized to update this user")
        
    user = await find_one("users", {"id": uid})
    if not user: raise HTTPException(404, "User not found")
    
    await update_one("users", {"id": uid}, {
        "username": u.username,
        "email": u.email,
    })
    return {"success": True}

@router.delete("/{uid}")
async def delete_user(uid: str, admin: dict = Depends(auth.get_admin_user)):
    ok = await delete_one("users", {"id": uid})
    if not ok: raise HTTPException(404, "User not found")
    return {"success": True}
