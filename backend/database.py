"""
In-memory database with JSON file persistence.
No external database required — works out of the box.
Data is saved to db.json on every write and loaded on startup.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).parent / "db.json"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _new_id():
    return uuid.uuid4().hex[:24]


# In-memory collections
_db = {
    "players": [],
    "tournaments": [],
    "matches": [],
    "games": [],
    "bots": [],
}


def _save():
    """Persist to disk."""
    with open(DB_FILE, "w") as f:
        json.dump(_db, f, indent=2, default=str)


# Default collection names
_COLLECTIONS = ["players", "tournaments", "matches", "games", "bots"]


def _load():
    """Load from disk if exists, ensuring all collections are present."""
    global _db
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r") as f:
                _db = json.load(f)
            # Ensure any new collections are added
            for col in _COLLECTIONS:
                if col not in _db:
                    _db[col] = []
            print(f"Loaded database from {DB_FILE}")
        except Exception as e:
            print(f"Could not load {DB_FILE}: {e}, starting fresh")
    else:
        print("Starting with empty database")


# ---- CRUD helpers ----

def find_all(collection: str, query: dict = None, sort_key: str = None,
             sort_reverse: bool = True, limit: int = None) -> list[dict]:
    items = _db.get(collection, [])
    if query:
        result = []
        for item in items:
            match = True
            for k, v in query.items():
                if k == "$or":
                    match = any(
                        all(item.get(fk) == fv for fk, fv in cond.items())
                        for cond in v
                    )
                elif item.get(k) != v:
                    match = False
                    break
            if match:
                result.append(item)
        items = result
    if sort_key:
        # Use a safe key so None / mixed types don't break sorting.
        # Always sort by the string representation of the value.
        items = sorted(
            items,
            key=lambda x: str(x.get(sort_key, "")),
            reverse=sort_reverse,
        )
    if limit:
        items = items[:limit]
    return [dict(i) for i in items]


def find_one(collection: str, query: dict) -> dict | None:
    results = find_all(collection, query)
    return dict(results[0]) if results else None


def insert_one(collection: str, doc: dict) -> dict:
    if "id" not in doc:
        doc["id"] = _new_id()
    if "created_at" not in doc:
        doc["created_at"] = _now_iso()
    if collection not in _db:
        _db[collection] = []
    _db[collection].append(doc)
    _save()
    return dict(doc)


def update_one(collection: str, query: dict, update: dict) -> bool:
    items = _db.get(collection, [])
    for item in items:
        if all(item.get(k) == v for k, v in query.items()):
            for k, v in update.items():
                item[k] = v
            _save()
            return True
    return False


def update_inc(collection: str, query: dict, increments: dict) -> bool:
    items = _db.get(collection, [])
    for item in items:
        if all(item.get(k) == v for k, v in query.items()):
            for k, v in increments.items():
                item[k] = item.get(k, 0) + v
            _save()
            return True
    return False


def push_to_array(collection: str, query: dict, field: str, value) -> bool:
    items = _db.get(collection, [])
    for item in items:
        if all(item.get(k) == v for k, v in query.items()):
            if field not in item:
                item[field] = []
            item[field].append(value)
            _save()
            return True
    return False


def delete_one(collection: str, query: dict) -> bool:
    items = _db.get(collection, [])
    for i, item in enumerate(items):
        if all(item.get(k) == v for k, v in query.items()):
            _db[collection].pop(i)
            _save()
            return True
    return False


def count_documents(collection: str, query: dict = None) -> int:
    return len(find_all(collection, query or {}))


# ---- Lifecycle ----

async def connect_db():
    _load()


async def close_db():
    _save()
    print("💾 Database saved")
