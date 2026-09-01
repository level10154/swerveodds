"""5DollarFootballAPI integration - fixtures & odds for worldwide leagues.

Replaces TheSportsDB (the weakest of our 3 original sources for this use case -
no predictions support, rate-limited free tier, inconsistent data fields) with
a budget-friendly fixtures+odds provider. Pro plan limit: 10 requests/minute.

Design goals (per spec):
- Token-bucket rate limiter capped at 10 req/min, shared across all callers.
- Every fixture/odds request is BATCHED: one call per UTC day covers every
  league at once, instead of one call per match or per league.
- Reads X-RateLimit-Remaining on every response; pauses new requests when it
  drops below 2 (also honours 429 + Retry-After).
- MongoDB cache TTL extended to 10 minutes for this source specifically.
- Graceful fallback to cached data (never a hard error) when rate-limited.
"""
import os
import time
import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

BASE = "https://api.5dollarfootballapi.com/v1"
CACHE_TTL = 60 * 10  # 10 minutes, per requirements
ERROR_CACHE_TTL = 60  # short-lived negative cache: avoids re-burning the 10 req/min
                      # budget on every request while a key is invalid/service is down,
                      # while still recovering quickly once fixed.


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('FIVEDOLLAR_API_KEY', '')}",
        "Accept": "application/json",
    }


class _TokenBucket:
    """Shared bucket: capacity 10, refilled at 10 tokens / 60s (Pro plan limit)."""

    def __init__(self, capacity: int = 10, period: float = 60.0):
        self.capacity = capacity
        self.period = period
        self.tokens = float(capacity)
        self.updated = time.monotonic()
        self.blocked_until = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.capacity / self.period)
                self.updated = now
                wait = max(0.0, self.blocked_until - now)
                if not wait and self.tokens >= 1:
                    self.tokens -= 1
                    return
                if not wait:
                    wait = (1 - self.tokens) * self.period / self.capacity
            await asyncio.sleep(max(wait, 0.05))

    async def observe(self, resp: httpx.Response):
        """Read X-RateLimit-Remaining on every response; pause new requests below 2."""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining is None:
            return
        try:
            if int(remaining) < 2:
                delay = 6.0
                if reset:
                    try:
                        delay = max(1.0, float(reset) - time.time())
                    except ValueError:
                        pass
                async with self.lock:
                    self.blocked_until = max(self.blocked_until, time.monotonic() + delay)
        except ValueError:
            pass

    async def block_from_429(self, resp: httpx.Response):
        try:
            delay = float(resp.headers.get("Retry-After", "60"))
        except ValueError:
            delay = 60.0
        async with self.lock:
            self.blocked_until = max(self.blocked_until, time.monotonic() + delay)


_bucket = _TokenBucket(10, 60)


async def _get(db: AsyncIOMotorDatabase, cache_key: str, path: str, params: dict | None = None) -> dict:
    """Cached GET (10 min TTL) + token-bucket throttling + graceful 429 fallback."""
    now = datetime.now(timezone.utc)
    doc = await db.fivedollar_cache.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > now:
        return doc["data"]
    await _bucket.acquire()
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(f"{BASE}{path}", headers=_headers(), params=params or {})
    except Exception:
        if doc:
            return doc["data"]
        return {"data": [], "error": "network_error"}
    await _bucket.observe(r)
    if r.status_code == 429:
        await _bucket.block_from_429(r)
        if doc:
            return doc["data"]
        result = {"data": [], "error": "rate_limited"}
        await db.fivedollar_cache.update_one(
            {"_id": cache_key},
            {"$set": {"data": result, "expires_at": now + timedelta(seconds=ERROR_CACHE_TTL)}},
            upsert=True,
        )
        return result
    if r.status_code >= 400:
        if doc:
            return doc["data"]
        result = {"data": [], "error": f"http_{r.status_code}"}
        await db.fivedollar_cache.update_one(
            {"_id": cache_key},
            {"$set": {"data": result, "expires_at": now + timedelta(seconds=ERROR_CACHE_TTL)}},
            upsert=True,
        )
        return result
    try:
        data = r.json() or {}
    except Exception:
        data = {"data": []}
    await db.fivedollar_cache.update_one(
        {"_id": cache_key},
        {"$set": {"data": data, "expires_at": now + timedelta(seconds=CACHE_TTL)}},
        upsert=True,
    )
    return data


# Curated worldwide leagues (parity with the previous provider's coverage).
# Matched against each fixture's league/competition name (case-insensitive
# substring match) since fixtures are fetched in a single batched day-call
# covering every league at once.
WORLD_LEAGUES = [
    {"id": "MLS", "code": "MLS", "name": "Major League Soccer", "country": "United States"},
    {"id": "AAL", "code": "AAL", "name": "Australian A-League", "country": "Australia"},
    {"id": "CSL", "code": "CSL", "name": "Chinese Super League", "country": "China"},
    {"id": "APD", "code": "APD", "name": "Argentine Primera Divisi\u00f3n", "country": "Argentina"},
    {"id": "SPL", "code": "SPL", "name": "Scottish Premiership", "country": "Scotland"},
    {"id": "ITB", "code": "ITB", "name": "Italian Serie B", "country": "Italy"},
    {"id": "BE1", "code": "BE1", "name": "Belgian Pro League", "country": "Belgium"},
    {"id": "NO1", "code": "NO1", "name": "Norwegian Eliteserien", "country": "Norway"},
    {"id": "JP1", "code": "JP1", "name": "Japanese J1 League", "country": "Japan"},
    {"id": "SPL2", "code": "SPL2", "name": "Saudi Pro League", "country": "Saudi Arabia"},
    {"id": "RPL", "code": "RPL", "name": "Russian Premier League", "country": "Russia"},
    {"id": "TSL", "code": "TSL", "name": "Turkish S\u00fcper Lig", "country": "Turkey"},
    {"id": "GSL", "code": "GSL", "name": "Greek Super League", "country": "Greece"},
    {"id": "UPL", "code": "UPL", "name": "Ukrainian Premier League", "country": "Ukraine"},
    {"id": "DK1", "code": "DK1", "name": "Danish Superliga", "country": "Denmark"},
    {"id": "SE1", "code": "SE1", "name": "Swedish Allsvenskan", "country": "Sweden"},
    {"id": "MXL", "code": "MXL", "name": "Mexican Liga MX", "country": "Mexico"},
    {"id": "KR1", "code": "KR1", "name": "South Korean K League 1", "country": "South Korea"},
]


def avatar_url(name: str, bg: str = "0ea5e9") -> str | None:
    """Generate a fallback badge/crest via ui-avatars - no extra API call needed,
    which keeps us well under the 10 req/min budget."""
    if not name:
        return None
    parts = [p for p in name.split()[:2] if p]
    initials = "".join(p[0].upper() for p in parts) if parts else name[:2].upper()
    return f"https://ui-avatars.com/api/?name={initials}&background={bg}&color=fff&bold=true&format=png&size=64"


async def fixtures_for_day(db, date: str) -> list[dict]:
    """ONE batched call covering every league for a full UTC day (YYYY-MM-DD).
    Cached for 10 minutes so repeat dashboard loads never re-trigger a live call."""
    start = int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    end = start + 86400 - 1
    data = await _get(db, f"fixtures:{date}", "/fixtures", {
        "start_time": start, "end_time": end, "per_page": 50, "include": "odds",
    })
    return (data or {}).get("data") or []


def _fixture_league_name(f: dict) -> str:
    lg = f.get("league") or f.get("competition") or {}
    return (lg.get("name") or "").strip()


def _matches_league(f: dict, league_name: str) -> bool:
    fn = _fixture_league_name(f).lower()
    return bool(fn) and league_name.lower() in fn


async def league_fixtures_window(db, league_name: str, days: int, forward: bool = True) -> list[dict]:
    """Scan a window of days - each fetched via the same batched, cached
    day-call reused by every other league lookup - and return fixtures
    matching `league_name`."""
    out = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        d = today + timedelta(days=i if forward else -i)
        date_str = d.strftime("%Y-%m-%d")
        try:
            day_fixtures = await fixtures_for_day(db, date_str)
        except Exception:
            continue
        for f in day_fixtures:
            if _matches_league(f, league_name):
                out.append(f)
    return out


def normalize_fixture(f: dict) -> dict:
    """Convert a 5DollarFootballAPI fixture into our unified match shape."""
    home = f.get("home_team") or f.get("home") or {}
    away = f.get("away_team") or f.get("away") or {}
    lg = f.get("league") or f.get("competition") or {}
    status_raw = (f.get("status") or "").lower()
    status_map = {
        "ns": "SCHEDULED", "not_started": "SCHEDULED", "scheduled": "SCHEDULED",
        "live": "IN_PLAY", "in_play": "IN_PLAY", "1h": "IN_PLAY", "2h": "IN_PLAY",
        "ft": "FINISHED", "finished": "FINISHED", "aet": "FINISHED",
        "postponed": "POSTPONED", "cancelled": "CANCELLED", "canceled": "CANCELLED",
    }
    status = status_map.get(status_raw, "SCHEDULED")
    start = f.get("start_time") or f.get("starting_at")
    dt = None
    if isinstance(start, (int, float)):
        dt = datetime.fromtimestamp(start, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(start, str):
        dt = start
    home_name = home.get("name") or "Home"
    away_name = away.get("name") or "Away"
    scores = f.get("scores") or {}
    return {
        "id": f"5d-{f.get('id')}",
        "source": "5dollarfootball",
        "utcDate": dt,
        "status": status,
        "competition": {
            "id": lg.get("id"),
            "name": lg.get("name") or "Worldwide",
            "code": lg.get("name"),
            "emblem": avatar_url(lg.get("name"), "0ea5e9"),
        },
        "area": {"name": lg.get("country") or "", "flag": None},
        "homeTeam": {
            "id": home.get("id"),
            "name": home_name,
            "shortName": home_name,
            "crest": home.get("logo") or avatar_url(home_name, "7c3aed"),
        },
        "awayTeam": {
            "id": away.get("id"),
            "name": away_name,
            "shortName": away_name,
            "crest": away.get("logo") or avatar_url(away_name, "db2777"),
        },
        "score": {
            "fullTime": {
                "home": (scores.get("home") if isinstance(scores, dict) else None) or home.get("score"),
                "away": (scores.get("away") if isinstance(scores, dict) else None) or away.get("score"),
            }
        },
    }
