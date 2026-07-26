from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import football_api as fa
import sports_db as tsdb
import api_football as apif
from predictor import predict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="NerdyStats API")
api_router = APIRouter(prefix="/api")

logger = logging.getLogger("nerdystats")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def _serialize_match(m: dict, prediction: dict | None = None) -> dict:
    return {
        "id": m["id"],
        "utcDate": m["utcDate"],
        "status": m["status"],
        "minute": m.get("minute"),
        "matchday": m.get("matchday"),
        "competition": {
            "id": m["competition"]["id"],
            "name": m["competition"]["name"],
            "code": m["competition"]["code"],
            "emblem": m["competition"].get("emblem"),
        },
        "area": {"name": m["area"]["name"], "flag": m["area"].get("flag")},
        "homeTeam": {
            "id": m["homeTeam"]["id"],
            "name": m["homeTeam"]["name"],
            "shortName": m["homeTeam"].get("shortName"),
            "tla": m["homeTeam"].get("tla"),
            "crest": m["homeTeam"].get("crest"),
        },
        "awayTeam": {
            "id": m["awayTeam"]["id"],
            "name": m["awayTeam"]["name"],
            "shortName": m["awayTeam"].get("shortName"),
            "tla": m["awayTeam"].get("tla"),
            "crest": m["awayTeam"].get("crest"),
        },
        "score": m.get("score", {}),
        "prediction": prediction,
    }


@api_router.get("/")
async def root():
    return {"service": "NerdyStats API", "status": "ok"}


@api_router.get("/competitions")
async def competitions():
    return {"competitions": fa.TOP_COMPETITIONS}


@api_router.get("/world/leagues")
async def world_leagues():
    """Combined worldwide leagues (football-data + TheSportsDB curated + API-Football if subscribed)."""
    combined = []
    for c in fa.TOP_COMPETITIONS:
        combined.append({
            "id": f"fd-{c['code']}",
            "code": c["code"],
            "name": c["name"],
            "country": c["country"],
            "emblem": c.get("emblem"),
            "source": "football-data",
            "predictions": True,
        })
    # TheSportsDB curated leagues (already dedup'd against football-data)
    for l in tsdb.WORLD_LEAGUES:
        # Look up badge from cached TheSportsDB league info (7-day cache)
        emblem = None
        try:
            info = await tsdb.lookup_league(db, l["id"])
            league = ((info.get("leagues") or []) + [{}])[0]
            emblem = league.get("strBadge") or league.get("strLogo")
        except Exception:
            pass
        combined.append({
            "id": f"tsdb-{l['id']}",
            "code": l["code"],
            "name": l["name"],
            "country": l["country"],
            "emblem": emblem,
            "source": "thesportsdb",
            "predictions": False,
        })
    return {"count": len(combined), "leagues": combined}


@api_router.get("/world/matches/today")
async def world_matches_today():
    """Aggregate today's matches from football-data + TheSportsDB."""
    from datetime import datetime as _dt
    date = _dt.utcnow().strftime("%Y-%m-%d")
    matches = []
    try:
        d = await fa.get_today_matches(db)
        for m in d.get("matches", []):
            matches.append(_serialize_match(m))
    except Exception as e:
        logger.warning(f"fd today failed: {e}")
    # TheSportsDB day events
    try:
        d = await tsdb.day_events(db, date)
        for e in d.get("events") or []:
            matches.append(tsdb.normalize_event(e))
    except Exception as e:
        logger.warning(f"tsdb day failed: {e}")
    # Dedupe by (home,away,date)
    seen = set()
    unique = []
    for m in matches:
        key = f"{(m.get('homeTeam') or {}).get('name','')}-{(m.get('awayTeam') or {}).get('name','')}-{(m.get('utcDate') or '')[:10]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return {"count": len(unique), "matches": unique}


@api_router.get("/world/league/{league_ref}/next")
async def world_league_next(league_ref: str):
    """Next fixtures for a TheSportsDB league. league_ref must be like 'tsdb-4328'."""
    if not league_ref.startswith("tsdb-"):
        raise HTTPException(status_code=400, detail="Expected league ref format tsdb-<id>")
    lid = league_ref.split("-", 1)[1]
    try:
        info = await tsdb.lookup_league(db, lid)
        nxt = await tsdb.next_league_events(db, lid)
        past = await tsdb.past_league_events(db, lid)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    league = ((info.get("leagues") or []) + [{}])[0]
    return {
        "league": {
            "id": league.get("idLeague"),
            "name": league.get("strLeague"),
            "country": league.get("strCountry"),
            "badge": league.get("strBadge"),
            "logo": league.get("strLogo"),
            "description": (league.get("strDescriptionEN") or "")[:600],
            "currentSeason": league.get("strCurrentSeason"),
            "website": league.get("strWebsite"),
        },
        "upcoming": [tsdb.normalize_event(e) for e in (nxt.get("events") or [])],
        "recent": [tsdb.normalize_event(e) for e in (past.get("events") or [])][:10],
    }


@api_router.get("/world/league/{league_ref}/table")
async def world_league_table(league_ref: str):
    if not league_ref.startswith("tsdb-"):
        raise HTTPException(status_code=400, detail="Expected league ref format tsdb-<id>")
    lid = league_ref.split("-", 1)[1]
    info = await tsdb.lookup_league(db, lid)
    league = ((info.get("leagues") or []) + [{}])[0]
    season = league.get("strCurrentSeason") or "2025-2026"
    tbl = await tsdb.league_table(db, lid, season)
    rows = tbl.get("table") or []
    return {
        "league": {
            "id": league.get("idLeague"),
            "name": league.get("strLeague"),
            "country": league.get("strCountry"),
            "badge": league.get("strBadge"),
            "season": season,
        },
        "table": [
            {
                "position": r.get("intRank"),
                "team": {"id": r.get("idTeam"), "name": r.get("strTeam"), "crest": r.get("strTeamBadge")},
                "playedGames": r.get("intPlayed"),
                "won": r.get("intWin"),
                "draw": r.get("intDraw"),
                "lost": r.get("intLoss"),
                "goalsFor": r.get("intGoalsFor"),
                "goalsAgainst": r.get("intGoalsAgainst"),
                "goalDifference": r.get("intGoalDifference"),
                "points": r.get("intPoints"),
            }
            for r in rows
        ],
    }


@api_router.get("/apif/status")
async def apif_status():
    """Check API-Football subscription status."""
    data = await apif.status(db)
    resp = (data.get("response") or {})
    if data.get("error"):
        return {"subscribed": False, "error": data.get("error"), "message": "Subscribe to API-Football free plan on RapidAPI marketplace to unlock 1000+ leagues."}
    return {"subscribed": True, "account": resp.get("account"), "subscription": resp.get("subscription"), "requests": resp.get("requests")}


@api_router.get("/apif/leagues")
async def apif_leagues():
    data = await apif.leagues(db, current=True)
    if data.get("error"):
        raise HTTPException(status_code=402, detail=data.get("error"))
    return {"count": len(data.get("response") or []), "leagues": data.get("response") or []}


@api_router.get("/apif/fixtures")
async def apif_fixtures(date: str):
    data = await apif.fixtures_by_date(db, date)
    if data.get("error"):
        raise HTTPException(status_code=402, detail=data.get("error"))
    return {"count": len(data.get("response") or []), "matches": [apif.normalize_fixture(f) for f in (data.get("response") or [])]}


@api_router.get("/matches/today")
async def matches_today(with_prediction: bool = False):
    data = await fa.get_today_matches(db)
    matches = data.get("matches", [])
    out = []
    for m in matches:
        pred = None
        if with_prediction and m.get("status") in ("TIMED", "SCHEDULED", "IN_PLAY", "PAUSED"):
            pred = await _build_prediction(m)
        out.append(_serialize_match(m, pred))
    return {"count": len(out), "matches": out}


@api_router.get("/matches/range")
async def matches_range(date_from: str, date_to: str, with_prediction: bool = False):
    data = await fa.get_matches_for_date_range(db, date_from, date_to)
    matches = data.get("matches", [])
    out = []
    for m in matches:
        pred = None
        if with_prediction and m.get("status") in ("TIMED", "SCHEDULED"):
            pred = await _build_prediction(m)
        out.append(_serialize_match(m, pred))
    return {"count": len(out), "matches": out}


@api_router.get("/predictions/today")
async def predictions_today(limit: int = 12):
    """Top upcoming matches today with predictions attached."""
    data = await fa.get_today_matches(db)
    matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED", "IN_PLAY")]
    matches = matches[:limit]
    out = []
    for m in matches:
        pred = await _build_prediction(m)
        out.append(_serialize_match(m, pred))
    return {"count": len(out), "matches": out}


@api_router.get("/predictions/upcoming")
async def predictions_upcoming(days: int = 3, limit: int = 12):
    limit = min(limit, 15)
    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    data = await fa.get_matches_for_date_range(db, date_from, date_to)
    matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")]
    matches = matches[:limit]
    out = []
    for m in matches:
        pred = await _build_prediction(m)
        out.append(_serialize_match(m, pred))
    return {"count": len(out), "matches": out}


@api_router.get("/predictions/bet-of-the-day")
async def bet_of_the_day():
    data = await fa.get_today_matches(db)
    matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")]
    best = None
    best_match = None
    best_pred = None
    for m in matches[:6]:
        pred = await _build_prediction(m)
        conf = pred["best_bet"]["confidence"]
        if best is None or conf > best:
            best = conf
            best_match = m
            best_pred = pred
    if not best_match:
        # fallback: pick from next 3 days
        date_from = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
        data = await fa.get_matches_for_date_range(db, date_from, date_to)
        matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")][:10]
        for m in matches:
            pred = await _build_prediction(m)
            conf = pred["best_bet"]["confidence"]
            if best is None or conf > best:
                best = conf
                best_match = m
                best_pred = pred
    if not best_match:
        raise HTTPException(status_code=404, detail="No matches available for bet of the day")
    return _serialize_match(best_match, best_pred)


@api_router.get("/match/{match_id}")
async def match_detail(match_id: int):
    try:
        data = await fa.get_match(db, match_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Match not found: {e}")
    m = data.get("match") or data
    pred = await _build_prediction(m)
    return _serialize_match(m, pred)


@api_router.get("/standings/{comp_code}")
async def standings(comp_code: str):
    try:
        data = await fa.get_standings(db, comp_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return data


@api_router.get("/competition/{comp_code}/matches")
async def competition_matches(comp_code: str, status: str | None = None):
    try:
        data = await fa.get_competition_matches(db, comp_code, status)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    matches = data.get("matches", [])
    return {"count": len(matches), "matches": [_serialize_match(m) for m in matches]}


@api_router.get("/competition/{comp_code}/scorers")
async def competition_scorers(comp_code: str):
    try:
        data = await fa.get_scorers(db, comp_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return data


async def _build_prediction(m: dict) -> dict:
    home_id = m["homeTeam"]["id"]
    away_id = m["awayTeam"]["id"]
    match_id = m.get("id")
    # Check prediction cache first (15 min TTL)
    if match_id:
        cache_doc = await db.prediction_cache.find_one({"_id": match_id})
        if cache_doc and cache_doc.get("expires_at") and cache_doc["expires_at"] > datetime.utcnow():
            return cache_doc["data"]
    try:
        home_data = await fa.get_team_matches(db, home_id, limit=10)
        away_data = await fa.get_team_matches(db, away_id, limit=10)
    except Exception as e:
        logger.warning(f"team fetch failed: {e}")
        home_data = {"matches": []}
        away_data = {"matches": []}
    pred = predict(home_data.get("matches", []), away_data.get("matches", []), home_id, away_id)
    if match_id:
        await db.prediction_cache.update_one(
            {"_id": match_id},
            {"$set": {"data": pred, "expires_at": datetime.utcnow() + timedelta(minutes=15)}},
            upsert=True,
        )
    return pred


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
