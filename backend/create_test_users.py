import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _new_id():
    return uuid.uuid4().hex[:24]

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['pahtum']
    
    password_hash = get_password_hash("1234")
    colors = ["#f87171", "#fb923c", "#fbbf24", "#34d399", "#38bdf8", "#818cf8", "#a78bfa", "#f472b6", "#9ca3af", "#4ade80"]
    
    users_to_insert = []
    for i in range(1, 11):
        username = f"testuser_{i}"
        user_doc = {
            "_id": _new_id(),
            "username": username,
            "name": f"Vague Account {i}",
            "avatar_color": colors[i-1],
            "email": f"testuser{i}@example.com",
            "password_hash": password_hash,
            "role": "USER",
            "created_at": _now_iso()
        }
        # Check if exists
        existing = await db.users.find_one({"username": username})
        if not existing:
            users_to_insert.append(user_doc)
    
    if users_to_insert:
        await db.users.insert_many(users_to_insert)
        print(f"Successfully created {len(users_to_insert)} test users (testuser_1 to testuser_10).")
    else:
        print("Test users already exist.")
        
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
