"""API-Football (RapidAPI) integration.
Requires the user to be subscribed to the free plan on RapidAPI.
Free plan: 100 requests/day. We cache HEAVILY.
"""
import os
import httpx
import time
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

HOST = "api-football-v1.p.rapidapi.com"
BASE = f"https://{HOST}/v3"


def _headers() -> dict:
    return {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": HOST,
    }


# Cache TTLs -- very long due to 100 req/day limit
TTL = {
    "status": 60 * 60,          # 1h
    "leagues": 60 * 60 * 24,    # 24h
    "fixtures_day": 60 * 30,    # 30 min
    "fixtures_live": 60 * 5,    # 5 min
    "standings": 60 * 60 * 6,   # 6h
    "predictions": 60 * 60 * 6, # 6h
}

_last_call = 0.0
_lock = asyncio.Lock()


async def _get(db, cache_key: str, kind: str, path: str, params: dict | None = None) -> dict:
    global _last_call
    ttl = TTL.get(kind, 60 * 60)
    now = datetime.utcnow()
    doc = await db.apif_cache.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > now:
        return doc["data"]
    async with _lock:
        # Soft spacing
        delta = time.time() - _last_call
        if delta < 1.5:
            await asyncio.sleep(1.5 - delta)
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                r = await c.get(f"{BASE}{path}", headers=_headers(), params=params or {})
            _last_call = time.time()
        except Exception as e:
            if doc: return doc["data"]
            return {"error": str(e), "response": []}
    if r.status_code >= 400:
        # subscription/quota errors: keep stale cache if any
        if doc: return doc["data"]
        try:
            return {"error": r.json(), "status": r.status_code, "response": []}
        except Exception:
            return {"error": r.text, "status": r.status_code, "response": []}
    try:
        data = r.json()
    except Exception:
        data = {}
    await db.apif_cache.update_one(
        {"_id": cache_key},
        {"$set": {"data": data, "expires_at": now + timedelta(seconds=ttl)}},
        upsert=True,
    )
    return data


async def status(db):
    return await _get(db, "status", "status", "/status")


async def leagues(db, current: bool = True):
    key = f"leagues:{'current' if current else 'all'}"
    params = {"current": "true"} if current else {}
    return await _get(db, key, "leagues", "/leagues", params)


async def fixtures_by_date(db, date: str):
    key = f"fixtures_day:{date}"
    return await _get(db, key, "fixtures_day", "/fixtures", {"date": date})


async def fixtures_live(db):
    return await _get(db, "fixtures_live", "fixtures_live", "/fixtures", {"live": "all"})


async def standings(db, league_id: int, season: int):
    key = f"standings:{league_id}:{season}"
    return await _get(db, key, "standings", "/standings", {"league": league_id, "season": season})


async def prediction(db, fixture_id: int):
    return await _get(db, f"prediction:{fixture_id}", "predictions", "/predictions", {"fixture": fixture_id})


def normalize_fixture(f: dict) -> dict:
    """Convert an API-Football fixture to our unified match shape."""
    fix = f.get("fixture", {})
    lg = f.get("league", {})
    tm = f.get("teams", {})
    gl = f.get("goals", {})
    st = (fix.get("status") or {}).get("short", "NS")
    status_map = {
        "NS": "SCHEDULED", "TBD": "SCHEDULED", "1H": "IN_PLAY", "2H": "IN_PLAY",
        "ET": "IN_PLAY", "P": "IN_PLAY", "HT": "PAUSED", "FT": "FINISHED",
        "AET": "FINISHED", "PEN": "FINISHED", "BT": "IN_PLAY", "LIVE": "IN_PLAY",
        "SUSP": "PAUSED", "INT": "PAUSED",
    }
    return {
        "id": f"apif-{fix.get('id')}",
        "source": "apifootball",
        "utcDate": fix.get("date"),
        "status": status_map.get(st, "SCHEDULED"),
        "minute": (fix.get("status") or {}).get("elapsed"),
        "competition": {
            "id": lg.get("id"),
            "name": lg.get("name"),
            "code": lg.get("country", "")[:3].upper() if lg.get("country") else None,
            "emblem": lg.get("logo"),
        },
        "area": {"name": lg.get("country") or "", "flag": lg.get("flag")},
        "homeTeam": {
            "id": (tm.get("home") or {}).get("id"),
            "name": (tm.get("home") or {}).get("name"),
            "shortName": (tm.get("home") or {}).get("name"),
            "crest": (tm.get("home") or {}).get("logo"),
        },
        "awayTeam": {
            "id": (tm.get("away") or {}).get("id"),
            "name": (tm.get("away") or {}).get("name"),
            "shortName": (tm.get("away") or {}).get("name"),
            "crest": (tm.get("away") or {}).get("logo"),
        },
        "score": {"fullTime": {"home": gl.get("home"), "away": gl.get("away")}},
        "venue": (fix.get("venue") or {}).get("name"),
    }
