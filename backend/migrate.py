import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['pahtum']
    users = await db.users.find({}).to_list(length=None)
    for u in users:
        updates = {}
        if 'name' not in u:
            updates['name'] = u.get('username', 'Unknown')
        if 'avatar_color' not in u:
            updates['avatar_color'] = '#8b5cf6'
        if updates:
            await db.users.update_one({'_id': u['_id']}, {'$set': updates})
            print(f"Updated user {u.get('username')}")
    print('Done migrating users.')
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
