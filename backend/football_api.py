"""Football-data.org API client with MongoDB caching to avoid rate limits."""
import os
import time
import httpx
import asyncio
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

API_BASE = "https://api.football-data.org/v4"


def _get_api_key() -> str:
    return os.environ.get("FOOTBALL_DATA_API_KEY", "")

# Cache TTLs (seconds) per endpoint kind
TTL = {
    "competitions": 60 * 60 * 24,      # 24h
    "standings": 60 * 30,               # 30min
    "matches_today": 60 * 5,            # 5min
    "matches_range": 60 * 15,           # 15min
    "team_matches": 60 * 30,            # 30min
    "match": 60 * 5,                    # 5min
    "competition_matches": 60 * 15,
    "scorers": 60 * 60,
}

_last_call_ts = 0.0
_call_lock = asyncio.Lock()


async def _rate_limited_get(path: str, params: dict | None = None) -> dict:
    """Perform GET with soft rate limit (6 sec between live calls)."""
    global _last_call_ts
    async with _call_lock:
        delta = time.time() - _last_call_ts
        if delta < 6.5:
            await asyncio.sleep(6.5 - delta)
        headers = {"X-Auth-Token": _get_api_key()}
        url = f"{API_BASE}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, headers=headers, params=params or {})
        _last_call_ts = time.time()
        if r.status_code == 429:
            # Backoff and retry once
            await asyncio.sleep(20)
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get(url, headers=headers, params=params or {})
            _last_call_ts = time.time()
        r.raise_for_status()
        return r.json()


async def cached_get(db: AsyncIOMotorDatabase, cache_key: str, kind: str, path: str, params: dict | None = None) -> dict:
    """Fetch from cache first, otherwise call API and store."""
    ttl = TTL.get(kind, 60 * 10)
    now = datetime.utcnow()
    doc = await db.api_cache.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > now:
        return doc["data"]
    try:
        data = await _rate_limited_get(path, params)
    except Exception as e:
        # Stale-if-error: return stale cache if available
        if doc:
            return doc["data"]
        raise e
    await db.api_cache.update_one(
        {"_id": cache_key},
        {"$set": {"data": data, "expires_at": now + timedelta(seconds=ttl), "updated_at": now}},
        upsert=True,
    )
    return data


# Top leagues we surface in the UI
TOP_COMPETITIONS = [
    {"code": "PL", "id": 2021, "name": "Premier League", "country": "England", "emblem": "https://crests.football-data.org/PL.png"},
    {"code": "PD", "id": 2014, "name": "La Liga", "country": "Spain", "emblem": "https://crests.football-data.org/PD.png"},
    {"code": "BL1", "id": 2002, "name": "Bundesliga", "country": "Germany", "emblem": "https://crests.football-data.org/BL1.png"},
    {"code": "SA", "id": 2019, "name": "Serie A", "country": "Italy", "emblem": "https://crests.football-data.org/SA.png"},
    {"code": "FL1", "id": 2015, "name": "Ligue 1", "country": "France", "emblem": "https://crests.football-data.org/FL1.png"},
    {"code": "DED", "id": 2003, "name": "Eredivisie", "country": "Netherlands", "emblem": "https://crests.football-data.org/DED.png"},
    {"code": "PPL", "id": 2017, "name": "Primeira Liga", "country": "Portugal", "emblem": "https://crests.football-data.org/PPL.png"},
    {"code": "BSA", "id": 2013, "name": "Brasileir\u00e3o", "country": "Brazil", "emblem": "https://crests.football-data.org/BSA.png"},
    {"code": "CL", "id": 2001, "name": "Champions League", "country": "Europe", "emblem": "https://crests.football-data.org/CL.png"},
    {"code": "ELC", "id": 2016, "name": "Championship", "country": "England", "emblem": "https://crests.football-data.org/ELC.png"},
    {"code": "CLI", "id": 2152, "name": "Copa Libertadores", "country": "South America", "emblem": "https://crests.football-data.org/CLI.png"},
]


async def get_matches_for_date_range(db, date_from: str, date_to: str):
    key = f"matches:{date_from}:{date_to}"
    return await cached_get(db, key, "matches_range", "/matches", {"dateFrom": date_from, "dateTo": date_to})


async def get_today_matches(db):
    from datetime import datetime, timedelta
    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    key = f"matches:today:{today}"
    return await cached_get(db, key, "matches_today", "/matches", {"dateFrom": today, "dateTo": tomorrow})


async def get_standings(db, comp_code: str):
    key = f"standings:{comp_code}"
    return await cached_get(db, key, "standings", f"/competitions/{comp_code}/standings")


async def get_competition_matches(db, comp_code: str, status: str | None = None):
    key = f"comp_matches:{comp_code}:{status or 'all'}"
    params = {"status": status} if status else None
    return await cached_get(db, key, "competition_matches", f"/competitions/{comp_code}/matches", params)


async def get_team_matches(db, team_id: int, limit: int = 10):
    key = f"team_matches:{team_id}:{limit}"
    return await cached_get(db, key, "team_matches", f"/teams/{team_id}/matches", {"limit": limit, "status": "FINISHED"})


async def get_match(db, match_id: int):
    key = f"match:{match_id}"
    return await cached_get(db, key, "match", f"/matches/{match_id}")


async def get_scorers(db, comp_code: str):
    key = f"scorers:{comp_code}"
    return await cached_get(db, key, "scorers", f"/competitions/{comp_code}/scorers", {"limit": 10})
