import asyncio
from database import connect_db, find_all, update_one, find_one

async def fix_leaderboard():
    await connect_db()
    
    # 1. Reset all user stats
    users = await find_all("users", {})
    for u in users:
        await update_one("users", {"id": u["id"]}, {
            "matches_played": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "total_score": 0
        })
    print("Reset stats for all users.")

    # 2. Re-calculate stats from completed matches
    matches = await find_all("matches", {"status": "completed"})
    for m in matches:
        winner = m.get("winner")
        if not winner: continue
        
        for pid_key, score_key, role in [
            ("player_white_id", "white_score", "white"),
            ("player_black_id", "black_score", "black"),
        ]:
            pid = m.get(pid_key)
            if not pid or pid in ("AI", "BYE"):
                continue
                
            target_user_id = pid
            if pid.startswith("bot:"):
                bot = await find_one("bots", {"id": pid[4:]})
                if bot and bot.get("owner_id"):
                    target_user_id = bot["owner_id"]
                else:
                    target_user_id = None
                    
            if target_user_id:
                # Need to find current stats of user to increment
                user = await find_one("users", {"id": target_user_id})
                if user:
                    upd = {
                        "matches_played": user.get("matches_played", 0) + 1,
                        "total_score": user.get("total_score", 0) + m.get(score_key, 0)
                    }
                    if winner == role:
                        upd["wins"] = user.get("wins", 0) + 1
                    elif winner == "draw":
                        upd["draws"] = user.get("draws", 0) + 1
                    else:
                        upd["losses"] = user.get("losses", 0) + 1
                        
                    await update_one("users", {"id": target_user_id}, upd)
                    
    print(f"Re-calculated leaderboard using {len(matches)} completed matches.")

if __name__ == "__main__":
    asyncio.run(fix_leaderboard())
