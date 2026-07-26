"""SportApi7 (RapidAPI) integration - SofaScore-mirror API with 5000+ leagues.
Free tier: usually 100-500 requests/day, cached HEAVILY.
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

HOST = "sportapi7.p.rapidapi.com"
BASE = f"https://{HOST}"


def _headers() -> dict:
    return {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": HOST,
    }


TTL = {
    "live": 60 * 2,             # 2 min
    "tournament": 60 * 60 * 24, # 24h
    "seasons": 60 * 60 * 24 * 7,
    "standings": 60 * 60,       # 1h
    "events_last": 60 * 15,     # 15 min
    "events_next": 60 * 30,     # 30 min
    "round": 60 * 30,
    "team": 60 * 60 * 24,
    "team_events": 60 * 30,
    "event": 60 * 5,
    "categories": 60 * 60 * 24 * 7,
}

_last_call = 0.0
_lock = asyncio.Lock()


async def _get(db, cache_key: str, kind: str, path: str) -> dict:
    global _last_call
    ttl = TTL.get(kind, 60 * 30)
    now = datetime.utcnow()
    doc = await db.sapi7_cache.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > now:
        return doc["data"]
    async with _lock:
        delta = time.time() - _last_call
        if delta < 1.2:
            await asyncio.sleep(1.2 - delta)
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                r = await c.get(f"{BASE}{path}", headers=_headers())
            _last_call = time.time()
        except Exception as e:
            if doc: return doc["data"]
            return {"error": str(e)}
    if r.status_code >= 400:
        if doc: return doc["data"]
        try: err = r.json()
        except Exception: err = {"raw": r.text}
        return {"error": err, "status": r.status_code}
    try:
        data = r.json()
    except Exception:
        data = {}
    await db.sapi7_cache.update_one(
        {"_id": cache_key},
        {"$set": {"data": data, "expires_at": now + timedelta(seconds=ttl)}},
        upsert=True,
    )
    return data


# --- Curated tournament IDs (SofaScore/SportApi7). Free tier friendly. ---
# Includes leagues NOT already covered by football-data.org so we don't duplicate.
TOURNAMENTS = [
    # Football-data has these too, but SportApi7 gives richer live data
    {"id": 17, "name": "Premier League", "country": "England", "season": 76986, "code": "PL"},
    {"id": 8, "name": "La Liga", "country": "Spain", "season": 77559, "code": "PD"},
    {"id": 35, "name": "Bundesliga", "country": "Germany", "season": 77333, "code": "BL1"},
    {"id": 23, "name": "Serie A", "country": "Italy", "season": 76457, "code": "SA"},
    {"id": 34, "name": "Ligue 1", "country": "France", "season": 77356, "code": "FL1"},
    # Extra worldwide leagues (SportApi7 exclusive)
    {"id": 242, "name": "Major League Soccer", "country": "United States", "season": 71156, "code": "MLS"},
    {"id": 325, "name": "J1 League", "country": "Japan", "season": 70083, "code": "JP1"},
    {"id": 955, "name": "Saudi Pro League", "country": "Saudi Arabia", "season": 77341, "code": "SPL"},
    {"id": 155, "name": "Liga MX", "country": "Mexico", "season": 77067, "code": "MXL"},
    {"id": 265, "name": "Argentine Primera", "country": "Argentina", "season": 72711, "code": "APD"},
    {"id": 52, "name": "Eredivisie", "country": "Netherlands", "season": 76841, "code": "DED"},
    {"id": 238, "name": "Primeira Liga", "country": "Portugal", "season": 77338, "code": "PPL"},
    {"id": 55, "name": "Chinese Super League", "country": "China", "season": 76693, "code": "CSL"},
    {"id": 71, "name": "Turkish S\u00fcper Lig", "country": "Turkey", "season": 77191, "code": "TSL"},
    {"id": 39, "name": "Jupiler Pro League", "country": "Belgium", "season": 77338, "code": "BE1"},
    {"id": 82, "name": "Scottish Premiership", "country": "Scotland", "season": 77128, "code": "SPL2"},
    {"id": 152, "name": "A-League", "country": "Australia", "season": 67552, "code": "AAL"},
    {"id": 296, "name": "K League 1", "country": "South Korea", "season": 77477, "code": "KR1"},
    {"id": 27, "name": "Serie B", "country": "Italy", "season": 76458, "code": "ITB"},
    {"id": 25, "name": "Bundesliga 2", "country": "Germany", "season": 77335, "code": "BL2"},
    {"id": 384, "name": "Brasileir\u00e3o", "country": "Brazil", "season": 72032, "code": "BSA"},
    {"id": 24, "name": "Championship", "country": "England", "season": 76988, "code": "ELC"},
    {"id": 7, "name": "Champions League", "country": "Europe", "season": 76953, "code": "CL"},
    {"id": 679, "name": "Europa League", "country": "Europe", "season": 76984, "code": "EL"},
]


async def live_events(db):
    return await _get(db, "live", "live", "/api/v1/sport/football/events/live")


async def tournament_info(db, tid: int):
    return await _get(db, f"t:{tid}", "tournament", f"/api/v1/unique-tournament/{tid}")


async def tournament_seasons(db, tid: int):
    return await _get(db, f"tseasons:{tid}", "seasons", f"/api/v1/unique-tournament/{tid}/seasons")


async def standings(db, tid: int, sid: int):
    return await _get(db, f"standings:{tid}:{sid}", "standings", f"/api/v1/unique-tournament/{tid}/season/{sid}/standings/total")


async def events_last(db, tid: int, sid: int, page: int = 0):
    return await _get(db, f"last:{tid}:{sid}:{page}", "events_last", f"/api/v1/unique-tournament/{tid}/season/{sid}/events/last/{page}")


async def events_round(db, tid: int, sid: int, rnd: int):
    return await _get(db, f"round:{tid}:{sid}:{rnd}", "round", f"/api/v1/unique-tournament/{tid}/season/{sid}/events/round/{rnd}")


async def tournament_rounds(db, tid: int, sid: int):
    return await _get(db, f"rounds:{tid}:{sid}", "round", f"/api/v1/unique-tournament/{tid}/season/{sid}/rounds")


async def team_info(db, tid: int):
    return await _get(db, f"team:{tid}", "team", f"/api/v1/team/{tid}")


async def team_last(db, tid: int, page: int = 0):
    return await _get(db, f"tlast:{tid}:{page}", "team_events", f"/api/v1/team/{tid}/events/last/{page}")


async def team_next(db, tid: int, page: int = 0):
    return await _get(db, f"tnext:{tid}:{page}", "team_events", f"/api/v1/team/{tid}/events/next/{page}")


async def event_detail(db, eid: int):
    return await _get(db, f"event:{eid}", "event", f"/api/v1/event/{eid}")


def _status_from_sofa(e: dict) -> str:
    st = ((e.get("status") or {}).get("type") or "").lower()
    m = {"inprogress": "IN_PLAY", "finished": "FINISHED", "notstarted": "SCHEDULED", "canceled": "CANCELLED", "postponed": "POSTPONED"}
    return m.get(st, "SCHEDULED")


def _team_crest(team_id, team_name: str) -> str:
    """Generate a fallback team crest using UI Avatars (free, no auth)."""
    if not team_name:
        return None
    # Take first letters of first two words
    parts = [p for p in team_name.split()[:2] if p]
    initials = "".join(p[0].upper() for p in parts) if parts else team_name[:2].upper()
    return f"https://ui-avatars.com/api/?name={initials}&background=7c3aed&color=fff&bold=true&format=png&size=64"


def normalize_event(e: dict) -> dict:
    t = e.get("tournament") or {}
    cat = (t.get("category") or {})
    ut = (e.get("tournament") or {}).get("uniqueTournament") or {}
    ts = e.get("startTimestamp")
    dt = None
    if ts:
        dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    home = e.get("homeTeam") or {}
    away = e.get("awayTeam") or {}
    hs = (e.get("homeScore") or {}).get("current")
    as_ = (e.get("awayScore") or {}).get("current")
    return {
        "id": f"sa7-{e.get('id')}",
        "source": "sportapi7",
        "utcDate": dt,
        "status": _status_from_sofa(e),
        "minute": ((e.get("time") or {}).get("currentPeriodStartTimestamp") and None),
        "competition": {
            "id": ut.get("id") or t.get("id"),
            "name": t.get("name") or ut.get("name"),
            "code": t.get("slug") or ut.get("slug"),
            "emblem": None,
        },
        "area": {"name": cat.get("name") or "", "flag": None, "country": cat.get("country", {}).get("alpha2")},
        "homeTeam": {
            "id": home.get("id"),
            "name": home.get("name"),
            "shortName": home.get("shortName") or home.get("name"),
            "crest": _team_crest(home.get("id"), home.get("name")),
        },
        "awayTeam": {
            "id": away.get("id"),
            "name": away.get("name"),
            "shortName": away.get("shortName") or away.get("name"),
            "crest": _team_crest(away.get("id"), away.get("name")),
        },
        "score": {
            "fullTime": {"home": hs, "away": as_},
            "halfTime": {"home": (e.get("homeScore") or {}).get("period1"), "away": (e.get("awayScore") or {}).get("period1")},
        },
    }
