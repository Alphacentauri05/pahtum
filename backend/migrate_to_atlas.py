import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

LOCAL_URI = "mongodb://localhost:27017"
# IMPORTANT: Replace <db_password> below with your actual password!
ATLAS_URI = "mongodb+srv://kushi:uday2003@cluster0.z35yzc7.mongodb.net/?appName=Cluster0"
DB_NAME = "pahtum"

COLLECTIONS = ["users", "tournaments", "matches", "bots"]

async def migrate():
    print("Connecting to databases...")
    try:
        local_client = AsyncIOMotorClient(LOCAL_URI)
        atlas_client = AsyncIOMotorClient(ATLAS_URI)
        
        local_db = local_client[DB_NAME]
        atlas_db = atlas_client[DB_NAME]
        
        for coll_name in COLLECTIONS:
            print(f"\nMigrating collection: '{coll_name}'...")
            
            # Fetch all documents from local database
            cursor = local_db[coll_name].find({})
            docs = await cursor.to_list(length=None)
            
            if not docs:
                print(f" - It is empty locally. Skipping.")
                continue
                
            print(f" - Found {len(docs)} documents. Uploading to Atlas...")
            
            # Wipe the target collection in Atlas to avoid duplicate key errors
            await atlas_db[coll_name].delete_many({})
            
            # Insert the documents into Atlas
            await atlas_db[coll_name].insert_many(docs)
            print(f" - Uploaded successfully!")
            
        print("\n🎉 Migration Complete! Your Atlas database has all your data.")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        print("Make sure you replaced <db_password> with your actual password!")

if __name__ == "__main__":
    asyncio.run(migrate())
