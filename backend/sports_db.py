"""TheSportsDB integration for worldwide league browsing + supplementary fixtures.
Free key `3` is used by default; upgrade to Patreon key for full access.
"""
import os
import httpx
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')


def _key() -> str:
    return os.environ.get("THESPORTSDB_KEY", "3")


BASE = "https://www.thesportsdb.com/api/v1/json"

# Curated worldwide soccer leagues (id + display info). Verified accessible via free key.
# NOTE: Only leagues NOT already covered by football-data.org to avoid duplicates.
WORLD_LEAGUES = [
    {"id": "4346", "name": "Major League Soccer", "country": "United States", "code": "MLS"},
    {"id": "4356", "name": "Australian A-League", "country": "Australia", "code": "AAL"},
    {"id": "4359", "name": "Chinese Super League", "country": "China", "code": "CSL"},
    {"id": "4406", "name": "Argentine Primera Divisi\u00f3n", "country": "Argentina", "code": "APD"},
    {"id": "4330", "name": "Scottish Premiership", "country": "Scotland", "code": "SPL"},
    {"id": "4394", "name": "Italian Serie B", "country": "Italy", "code": "ITB"},
    {"id": "4340", "name": "Belgian Pro League", "country": "Belgium", "code": "BE1"},
    {"id": "4457", "name": "Norwegian Eliteserien", "country": "Norway", "code": "NO1"},
    {"id": "4481", "name": "Japanese J1 League", "country": "Japan", "code": "JP1"},
    {"id": "4387", "name": "Saudi Pro League", "country": "Saudi Arabia", "code": "SPL2"},
    {"id": "4358", "name": "Russian Premier League", "country": "Russia", "code": "RPL"},
    {"id": "4336", "name": "Turkish S\u00fcper Lig", "country": "Turkey", "code": "TSL"},
    {"id": "4339", "name": "Greek Super League", "country": "Greece", "code": "GSL"},
    {"id": "4341", "name": "Ukrainian Premier League", "country": "Ukraine", "code": "UPL"},
    {"id": "4342", "name": "Danish Superliga", "country": "Denmark", "code": "DK1"},
    {"id": "4345", "name": "Swedish Allsvenskan", "country": "Sweden", "code": "SE1"},
    {"id": "4361", "name": "Mexican Liga MX", "country": "Mexico", "code": "MXL"},
    {"id": "4480", "name": "South Korean K League 1", "country": "South Korea", "code": "KR1"},
]

TTL = {
    "league_lookup": 60 * 60 * 24 * 7,  # 7 days
    "league_next": 60 * 60,             # 1h
    "day_events": 60 * 20,              # 20 min
    "league_table": 60 * 60 * 6,        # 6h
}


async def _get(db: AsyncIOMotorDatabase, cache_key: str, kind: str, path: str) -> dict:
    ttl = TTL.get(kind, 60 * 30)
    now = datetime.utcnow()
    doc = await db.tsdb_cache.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > now:
        return doc["data"]
    url = f"{BASE}/{_key()}{path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url)
        r.raise_for_status()
        data = r.json() or {}
    except Exception as e:
        if doc:
            return doc["data"]
        return {}
    await db.tsdb_cache.update_one(
        {"_id": cache_key},
        {"$set": {"data": data, "expires_at": now + timedelta(seconds=ttl)}},
        upsert=True,
    )
    return data


async def lookup_league(db, league_id: str) -> dict:
    return await _get(db, f"league_lookup:{league_id}", "league_lookup", f"/lookupleague.php?id={league_id}")


async def next_league_events(db, league_id: str) -> dict:
    return await _get(db, f"league_next:{league_id}", "league_next", f"/eventsnextleague.php?id={league_id}")


async def past_league_events(db, league_id: str) -> dict:
    return await _get(db, f"league_past:{league_id}", "league_next", f"/eventspastleague.php?id={league_id}")


async def day_events(db, date: str) -> dict:
    """date format YYYY-MM-DD"""
    return await _get(db, f"day_events:{date}", "day_events", f"/eventsday.php?d={date}&s=Soccer")


async def league_table(db, league_id: str, season: str) -> dict:
    return await _get(db, f"league_table:{league_id}:{season}", "league_table", f"/lookuptable.php?l={league_id}&s={season}")


def normalize_event(e: dict) -> dict:
    """Convert a TheSportsDB event to our unified match shape."""
    dt = None
    if e.get("strTimestamp"):
        dt = e["strTimestamp"].replace(" ", "T") + "Z" if "T" not in e["strTimestamp"] else e["strTimestamp"]
    elif e.get("dateEvent") and e.get("strTime"):
        dt = f"{e['dateEvent']}T{e['strTime']}Z"
    return {
        "id": f"tsdb-{e.get('idEvent')}",
        "source": "thesportsdb",
        "utcDate": dt,
        "status": "FINISHED" if e.get("intHomeScore") not in (None, "") else "SCHEDULED",
        "competition": {
            "id": e.get("idLeague"),
            "name": e.get("strLeague"),
            "code": e.get("strLeague"),
            "emblem": e.get("strLeagueBadge"),
        },
        "area": {"name": e.get("strCountry") or "", "flag": None},
        "homeTeam": {
            "id": e.get("idHomeTeam"),
            "name": e.get("strHomeTeam"),
            "shortName": e.get("strHomeTeam"),
            "crest": e.get("strHomeTeamBadge") or None,
        },
        "awayTeam": {
            "id": e.get("idAwayTeam"),
            "name": e.get("strAwayTeam"),
            "shortName": e.get("strAwayTeam"),
            "crest": e.get("strAwayTeamBadge") or None,
        },
        "score": {
            "fullTime": {
                "home": int(e["intHomeScore"]) if str(e.get("intHomeScore") or "").isdigit() else None,
                "away": int(e["intAwayScore"]) if str(e.get("intAwayScore") or "").isdigit() else None,
            }
        },
        "venue": e.get("strVenue"),
    }
