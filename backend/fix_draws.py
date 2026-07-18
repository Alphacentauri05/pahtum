import asyncio
from database import find_all, update_one, find_one, connect_db

async def fix_draws():
    await connect_db()
    matches = await find_all("matches", {"winner": "draw"})
    count = 0
    for match in matches:
        if match.get("status") == "completed" and match.get("tournament_id"):
            t = await find_one("tournaments", {"id": match["tournament_id"]})
            if t and t.get("format") != "group_stage":
                print(f"Fixing draw for match {match['id']}")
                new_white = match.get("player_black_id")
                new_black = match.get("player_white_id")
                await update_one("matches", {"id": match["id"]}, {
                    "status": "scheduled",
                    "player_white_id": new_white,
                    "player_black_id": new_black,
                    "white_score": 0,
                    "black_score": 0,
                    "winner": None,
                    "moves": [],
                    "final_board": None
                })
                count += 1
    print(f"Fixed {count} matches.")

if __name__ == "__main__":
    asyncio.run(fix_draws())
