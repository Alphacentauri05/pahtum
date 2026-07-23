import os
import uuid
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _new_id():
    return uuid.uuid4().hex[:24]

DB_DIR = Path(__file__).parent / "data"
# Use environment variable if set (for deployment), otherwise default to your Atlas cluster
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kushi:uday2003@cluster0.z35yzc7.mongodb.net/?appName=Cluster0")
DB_NAME = "pahtum"

class MongoDBClient:
    def __init__(self):
        self.client = None
        self.db = None

    async def initialize(self):
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        print(f"MongoDB connected to {MONGO_URL}/{DB_NAME}")
        
        # Migration logic from legacy JSON files
        if DB_DIR.exists():
            print("Checking for legacy JSON data to migrate...")
            migrated = False
            for file in DB_DIR.glob("*.json"):
                collection = file.stem
                # Check if collection is empty in mongo
                count = await self.db[collection].count_documents({})
                if count == 0:
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data:
                            # Map id to _id
                            for doc in data:
                                if "id" in doc:
                                    doc["_id"] = doc["id"]
                                    del doc["id"]
                            await self.db[collection].insert_many(data)
                            print(f"Migrated {len(data)} documents into '{collection}' collection.")
                            migrated = True
                    except Exception as e:
                        print(f"Failed to migrate {file.name}: {e}")
                
                # Rename file so we don't migrate again
                try:
                    file.rename(file.with_suffix(".json.migrated"))
                except:
                    pass
                    
            if migrated:
                print("JSON Migration complete.")

    async def close(self):
        if self.client:
            self.client.close()

    def _map_query(self, query: dict) -> dict:
        if not query:
            return {}
        q = query.copy()
        if "id" in q:
            q["_id"] = q.pop("id")
        
        # Recursive mapping for $or lists
        if "$or" in q:
            q["$or"] = [self._map_query(subq) for subq in q["$or"]]
            
        return q

    def _map_doc(self, doc: dict) -> dict:
        if not doc:
            return doc
        d = doc.copy()
        if "_id" in d:
            d["id"] = d.pop("_id")
        return d

    async def find_all(self, collection: str, query: dict = None, sort_key: str = None,
                       sort_reverse: bool = True, limit: int = None) -> list[dict]:
        q = self._map_query(query)
        cursor = self.db[collection].find(q)
        
        if sort_key:
            direction = -1 if sort_reverse else 1
            # Special case for "id" -> "_id"
            mongo_sort = "_id" if sort_key == "id" else sort_key
            cursor = cursor.sort(mongo_sort, direction)
            
        if limit:
            cursor = cursor.limit(limit)
            
        docs = await cursor.to_list(length=limit or 1000)
        return [self._map_doc(d) for d in docs]

    async def find_one(self, collection: str, query: dict) -> dict | None:
        q = self._map_query(query)
        doc = await self.db[collection].find_one(q)
        return self._map_doc(doc) if doc else None

    async def insert_one(self, collection: str, doc: dict) -> dict:
        doc = doc.copy()
        if "id" not in doc:
            doc["id"] = _new_id()
        if "created_at" not in doc:
            doc["created_at"] = _now_iso()
            
        mongo_doc = doc.copy()
        mongo_doc["_id"] = mongo_doc.pop("id")
        
        await self.db[collection].insert_one(mongo_doc)
        return doc

    async def update_one(self, collection: str, query: dict, update: dict) -> bool:
        q = self._map_query(query)
        result = await self.db[collection].update_one(q, {"$set": update})
        return result.modified_count > 0

    async def update_inc(self, collection: str, query: dict, increments: dict) -> bool:
        q = self._map_query(query)
        result = await self.db[collection].update_one(q, {"$inc": increments})
        return result.modified_count > 0

    async def push_to_array(self, collection: str, query: dict, field: str, value) -> bool:
        q = self._map_query(query)
        result = await self.db[collection].update_one(q, {"$push": {field: value}})
        return result.modified_count > 0

    async def pull_from_array(self, collection: str, query: dict, field: str, value) -> bool:
        q = self._map_query(query)
        result = await self.db[collection].update_one(q, {"$pull": {field: value}})
        return result.modified_count > 0

    async def delete_one(self, collection: str, query: dict) -> bool:
        q = self._map_query(query)
        result = await self.db[collection].delete_one(q)
        return result.deleted_count > 0

    async def count_documents(self, collection: str, query: dict = None) -> int:
        q = self._map_query(query)
        return await self.db[collection].count_documents(q)


db_client = MongoDBClient()

# Export interface mapping to db_client methods
async def connect_db():
    await db_client.initialize()

async def close_db():
    await db_client.close()

async def find_all(collection: str, query: dict = None, sort_key: str = None, sort_reverse: bool = True, limit: int = None):
    return await db_client.find_all(collection, query, sort_key, sort_reverse, limit)

async def find_one(collection: str, query: dict):
    return await db_client.find_one(collection, query)

async def insert_one(collection: str, doc: dict):
    return await db_client.insert_one(collection, doc)

async def update_one(collection: str, query: dict, update: dict):
    return await db_client.update_one(collection, query, update)

async def update_inc(collection: str, query: dict, increments: dict):
    return await db_client.update_inc(collection, query, increments)

async def push_to_array(collection: str, query: dict, field: str, value):
    return await db_client.push_to_array(collection, query, field, value)

async def pull_from_array(collection: str, query: dict, field: str, value):
    return await db_client.pull_from_array(collection, query, field, value)

async def delete_one(collection: str, query: dict):
    return await db_client.delete_one(collection, query)

async def count_documents(collection: str, query: dict = None):
    return await db_client.count_documents(collection, query)
