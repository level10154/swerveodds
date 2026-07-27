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


# --- Curated tournament IDs (SofaScore/SportApi7). Season is fetched dynamically. ---
# IDs verified from live events response.
TOURNAMENTS = [
    # In-season worldwide leagues (verified live)
    {"id": 649, "name": "Chinese Super League", "country": "China", "code": "CSL"},
    {"id": 40, "name": "Allsvenskan", "country": "Sweden", "code": "SE1"},
    {"id": 215, "name": "Swiss Super League", "country": "Switzerland", "code": "CH1"},
    {"id": 410, "name": "K League 1", "country": "South Korea", "code": "KR1"},
    {"id": 39, "name": "Danish Superliga", "country": "Denmark", "code": "DK1"},
    {"id": 41, "name": "Veikkausliiga", "country": "Finland", "code": "FI1"},
    {"id": 47, "name": "Betinia Liga", "country": "Poland", "code": "PL2"},
    {"id": 777, "name": "K League 2", "country": "South Korea", "code": "KR2"},
    {"id": 782, "name": "Chinese League 1", "country": "China", "code": "CSL2"},
    # Big European leagues (will be in-season Aug+)
    {"id": 17, "name": "Premier League", "country": "England", "code": "PL"},
    {"id": 8, "name": "La Liga", "country": "Spain", "code": "PD"},
    {"id": 35, "name": "Bundesliga", "country": "Germany", "code": "BL1"},
    {"id": 23, "name": "Serie A", "country": "Italy", "code": "SA"},
    {"id": 34, "name": "Ligue 1", "country": "France", "code": "FL1"},
    # Other worldwide leagues
    {"id": 242, "name": "Major League Soccer", "country": "United States", "code": "MLS"},
    {"id": 325, "name": "J1 League", "country": "Japan", "code": "JP1"},
    {"id": 955, "name": "Saudi Pro League", "country": "Saudi Arabia", "code": "SPL"},
    {"id": 384, "name": "Brasileir\u00e3o", "country": "Brazil", "code": "BSA"},
    {"id": 155, "name": "Liga MX", "country": "Mexico", "code": "MXL"},
    {"id": 265, "name": "Argentine Primera", "country": "Argentina", "code": "APD"},
    {"id": 71, "name": "Turkish S\u00fcper Lig", "country": "Turkey", "code": "TSL"},
    {"id": 152, "name": "A-League", "country": "Australia", "code": "AAL"},
    {"id": 39, "name": "Jupiter Pro League", "country": "Belgium", "code": "BE1"},
    {"id": 7, "name": "Champions League", "country": "Europe", "code": "CL"},
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


def sa7_events_to_predictor_format(events: list[dict]) -> list[dict]:
    """Convert SportApi7 last events into the shape our predictor expects
    (homeTeam.id, awayTeam.id, score.fullTime.home/away, status)."""
    out = []
    for e in events:
        st = ((e.get("status") or {}).get("type") or "").lower()
        if st != "finished":
            continue
        hs = (e.get("homeScore") or {}).get("current")
        as_ = (e.get("awayScore") or {}).get("current")
        if hs is None or as_ is None:
            continue
        out.append({
            "status": "FINISHED",
            "homeTeam": {"id": (e.get("homeTeam") or {}).get("id")},
            "awayTeam": {"id": (e.get("awayTeam") or {}).get("id")},
            "score": {"fullTime": {"home": hs, "away": as_}},
        })
    return out


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
