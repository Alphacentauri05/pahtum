"""
Leaderboard and analytics routes.
"""
from fastapi import APIRouter
from database import find_all, count_documents

router = APIRouter(prefix="/api", tags=["leaderboard"])


@router.get("/leaderboard")
async def get_leaderboard():
    players = find_all("players", sort_key="wins", sort_reverse=True)
    for i, p in enumerate(players):
        p["rank"] = i + 1
    return players


@router.get("/stats/overview")
async def get_overview_stats():
    total_players = count_documents("players")
    total_matches = count_documents("matches")
    completed_matches = count_documents("matches", {"status": "completed"})
    active_tournaments = count_documents("tournaments", {"status": "active"})
    total_tournaments = count_documents("tournaments")

    recent = find_all("matches", {"status": "completed"}, sort_key="played_at", sort_reverse=True, limit=5)
    top = find_all("players", sort_key="wins", sort_reverse=True, limit=5)

    return {
        "total_players": total_players,
        "total_matches": total_matches,
        "completed_matches": completed_matches,
        "active_tournaments": active_tournaments,
        "total_tournaments": total_tournaments,
        "recent_matches": recent,
        "top_players": top,
    }
