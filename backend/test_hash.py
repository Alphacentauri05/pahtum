import asyncio
from database import find_one
async def test():
    user = await find_one("users", {"$or": [{"username": "uday"}, {"email": "uday"}]})
    print("User found by username:", user)
    user2 = await find_one("users", {"$or": [{"username": "udaysharma051203@gmail.com"}, {"email": "udaysharma051203@gmail.com"}]})
    print("User found by email:", user2)

asyncio.run(test())
