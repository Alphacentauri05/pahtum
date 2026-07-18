from fastapi import APIRouter
from database import find_all, count_documents

router = APIRouter(prefix="/api", tags=["leaderboard"])

@router.get("/leaderboard")
async def get_leaderboard():
    users = await find_all("users")
    # Sort in python to handle missing keys gracefully
    users.sort(key=lambda u: u.get("wins", 0), reverse=True)
    for i, u in enumerate(users):
        u["rank"] = i + 1
        u["name"] = u.get("name") or u.get("username") or "Unknown"
        u["avatar_color"] = u.get("avatar_color") or "#8b5cf6"
        u["wins"] = u.get("wins", 0)
        u["losses"] = u.get("losses", 0)
        u["total_score"] = u.get("total_score", 0)
        u.pop("password_hash", None)
    return users

@router.get("/stats/overview")
async def get_overview_stats():
    total_users = await count_documents("users")
    total_matches = await count_documents("matches")
    completed_matches = await count_documents("matches", {"status": "completed"})
    active_tournaments = await count_documents("tournaments", {"status": "active"})
    total_tournaments = await count_documents("tournaments")

    recent = await find_all("matches", {"status": "completed"}, sort_key="played_at", sort_reverse=True, limit=5)
    top = await find_all("users", sort_key="wins", sort_reverse=True, limit=5)
    for u in top:
        u.pop("password_hash", None)

    return {
        "total_players": total_users,
        "total_matches": total_matches,
        "completed_matches": completed_matches,
        "active_tournaments": active_tournaments,
        "total_tournaments": total_tournaments,
        "recent_matches": recent,
        "top_players": top,
    }
