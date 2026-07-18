import asyncio
from database import connect_db, find_all, delete_one, find_one, update_one

async def fix_finals():
    await connect_db()
    # Find the tournament "maharaja series" or just find matches in round 1 with "beta"
    matches = await find_all("matches", {"round_num": 1})
    print(f"Found {len(matches)} matches in round 1:")
    for m in matches:
        print(f"ID: {m['id']}, W: {m.get('player_white_id')}, B: {m.get('player_black_id')}")

    bogus_match = None
    beta_bot = await find_one("bots", {"name": "beta"})
    if not beta_bot:
        print("Beta bot not found in DB")
        return
        
    beta_id = f"bot:{beta_bot['id']}"
    print(f"Beta bot ID: {beta_id}")

    for m in matches:
        if m.get("player_white_id") == beta_id or m.get("player_black_id") == beta_id:
            bogus_match = m
            break
            
    if not bogus_match:
        print("Bogus match not found")
        return
        
    print(f"Found bogus match: {bogus_match['id']}")
    
    # Delete the match
    await delete_one("matches", {"id": bogus_match["id"]})
    print("Deleted bogus match from matches collection.")
    
    # Update the tournament rounds
    t_id = bogus_match["tournament_id"]
    t = await find_one("tournaments", {"id": t_id})
    if t and "rounds" in t and len(t["rounds"]) > 1:
        round1_ids = t["rounds"][1]
        if bogus_match["id"] in round1_ids:
            round1_ids.remove(bogus_match["id"])
            t["rounds"][1] = round1_ids
            await update_one("tournaments", {"id": t_id}, {"rounds": t["rounds"]})
            print("Removed bogus match from tournament rounds.")
            
    print("Fix complete!")

if __name__ == "__main__":
    asyncio.run(fix_finals())
