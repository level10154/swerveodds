from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import football_api as fa
import api_5dollar as f5  # 5DollarFootballAPI (replaces TheSportsDB)
import api_football as sa7  # SportApi7 (SofaScore mirror)
from predictor import predict, select_bets_of_day, BET_CONFIDENCE_THRESHOLD

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
    """Combined worldwide leagues (football-data + 5DollarFootballAPI curated + SportApi7 if subscribed)."""
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
    # 5DollarFootballAPI curated leagues (already dedup'd against football-data).
    # Badge is a generated avatar - zero extra API calls needed to stay well
    # under the 10 req/min budget.
    for l in f5.WORLD_LEAGUES:
        combined.append({
            "id": f"fivedollar-{l['code']}",
            "code": l["code"],
            "name": l["name"],
            "country": l["country"],
            "emblem": f5.avatar_url(l["name"]),
            "source": "fivedollarfootball",
            "predictions": False,
        })
    # SportApi7 tournaments (only unique ones not covered above)
    seen_names = {c["name"].lower() for c in combined}
    for t in sa7.TOURNAMENTS:
        if t["name"].lower() in seen_names:
            continue
        combined.append({
            "id": f"sa7-{t['id']}",
            "code": t["code"],
            "name": t["name"],
            "country": t["country"],
            "emblem": None,
            "source": "sportapi7",
            "predictions": False,
        })
    return {"count": len(combined), "leagues": combined}


@api_router.get("/world/matches/today")
async def world_matches_today():
    """Aggregate today's matches from football-data + 5DollarFootballAPI + SportApi7 live."""
    from datetime import datetime as _dt
    date = _dt.utcnow().strftime("%Y-%m-%d")
    matches = []
    try:
        d = await fa.get_today_matches(db)
        for m in d.get("matches", []):
            matches.append(_serialize_match(m))
    except Exception as e:
        logger.warning(f"fd today failed: {e}")
    # SportApi7 live events (worldwide)
    try:
        d = await sa7.live_events(db)
        for e in d.get("events") or []:
            matches.append(sa7.normalize_event(e))
    except Exception as e:
        logger.warning(f"sa7 live failed: {e}")
    # 5DollarFootballAPI - single batched call covers every league for today
    try:
        for fixture in await f5.fixtures_for_day(db, date):
            matches.append(f5.normalize_fixture(fixture))
    except Exception as e:
        logger.warning(f"5dollar day failed: {e}")
    # Dedupe by (home,away,date)
    seen = set()
    unique = []
    for m in matches:
        key = f"{(m.get('homeTeam') or {}).get('name','').lower()}-{(m.get('awayTeam') or {}).get('name','').lower()}-{(m.get('utcDate') or '')[:10]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return {"count": len(unique), "matches": unique}


@api_router.get("/world/league/{league_ref}/next")
async def world_league_next(league_ref: str):
    """Next & recent fixtures for a 5DollarFootballAPI curated league. league_ref must be like 'fivedollar-MLS'."""
    if not league_ref.startswith("fivedollar-"):
        raise HTTPException(status_code=400, detail="Expected league ref format fivedollar-<code>")
    code = league_ref.split("-", 1)[1]
    league = next((l for l in f5.WORLD_LEAGUES if l["code"] == code), None)
    if not league:
        raise HTTPException(status_code=404, detail="Unknown league code")
    # Bounded, timed window: 5 days forward + 3 back (8 day-calls worst case),
    # each day fetch shared/cached across every league. Hard-capped at 25s so a
    # cold cache (or an invalid 5dollar key) always degrades to an empty list
    # instead of hanging past the gateway's request timeout.
    async def _fetch_window():
        upcoming_raw = await f5.league_fixtures_window(db, league["name"], days=5, forward=True)
        recent_raw = await f5.league_fixtures_window(db, league["name"], days=3, forward=False)
        return upcoming_raw, recent_raw
    try:
        upcoming_raw, recent_raw = await asyncio.wait_for(_fetch_window(), timeout=25)
    except Exception:
        upcoming_raw, recent_raw = [], []
    upcoming = [f5.normalize_fixture(f) for f in upcoming_raw if (f.get("status") or "").lower() not in ("ft", "finished", "aet")]
    recent = [f5.normalize_fixture(f) for f in recent_raw if (f.get("status") or "").lower() in ("ft", "finished", "aet")]
    upcoming.sort(key=lambda m: m.get("utcDate") or "")
    recent.sort(key=lambda m: m.get("utcDate") or "", reverse=True)
    return {
        "league": {
            "id": league["id"],
            "name": league["name"],
            "country": league["country"],
            "badge": f5.avatar_url(league["name"]),
            "logo": f5.avatar_url(league["name"]),
            "description": "Fixtures & odds for this league are powered by 5DollarFootballAPI.",
            "currentSeason": None,
            "website": None,
        },
        "upcoming": upcoming[:10],
        "recent": recent[:10],
    }


@api_router.get("/world/league/{league_ref}/table")
async def world_league_table(league_ref: str):
    if not league_ref.startswith("fivedollar-"):
        raise HTTPException(status_code=400, detail="Expected league ref format fivedollar-<code>")
    code = league_ref.split("-", 1)[1]
    league = next((l for l in f5.WORLD_LEAGUES if l["code"] == code), None)
    if not league:
        raise HTTPException(status_code=404, detail="Unknown league code")
    # 5DollarFootballAPI does not expose a standings endpoint - return the same
    # graceful "not available" shape the frontend already handles.
    return {
        "league": {
            "id": league["id"],
            "name": league["name"],
            "country": league["country"],
            "badge": f5.avatar_url(league["name"]),
            "season": None,
        },
        "table": [],
    }


@api_router.get("/apif/status")
async def apif_status():
    """Check SportApi7 subscription status via live-events endpoint."""
    data = await sa7.live_events(db)
    if data.get("error"):
        return {"subscribed": False, "error": data.get("error"), "message": "Subscribe to SportApi7 on RapidAPI to unlock 5000+ leagues worldwide."}
    return {"subscribed": True, "live_events_count": len(data.get("events") or [])}


@api_router.get("/global/live")
async def global_live(limit: int = 40):
    """Live worldwide football matches from SportApi7."""
    data = await sa7.live_events(db)
    events = data.get("events") or []
    # Prioritise higher-tier leagues (category priority high or matches with lots of viewers)
    events.sort(key=lambda e: -(((e.get("tournament") or {}).get("category") or {}).get("priority", 0) or 0))
    matches = [sa7.normalize_event(e) for e in events[:limit]]
    return {"count": len(matches), "matches": matches}


@api_router.get("/global/tournaments")
async def global_tournaments():
    """Curated worldwide tournament list from SportApi7."""
    return {"count": len(sa7.TOURNAMENTS), "tournaments": sa7.TOURNAMENTS}


@api_router.get("/global/tournament/{tid}/standings")
async def global_tournament_standings(tid: int, season: int | None = None):
    if season is None:
        season = await _get_current_season(tid)
    if not season:
        raise HTTPException(status_code=400, detail="Season required")
    data = await sa7.standings(db, tid, season)
    if data.get("error"):
        raise HTTPException(status_code=502, detail=data.get("error"))
    return data


@api_router.get("/global/tournament/{tid}/events")
async def global_tournament_events(tid: int, season: int | None = None, page: int = 0):
    if season is None:
        season = await _get_current_season(tid)
    if not season:
        raise HTTPException(status_code=400, detail="Season required")
    last = await sa7.events_last(db, tid, season, page)
    events = last.get("events") or []
    matches = [sa7.normalize_event(e) for e in events]
    return {"count": len(matches), "matches": matches}


@api_router.get("/global/team/{tid}/next")
async def global_team_next(tid: int):
    data = await sa7.team_next(db, tid)
    events = data.get("events") or []
    return {"count": len(events), "matches": [sa7.normalize_event(e) for e in events]}


async def _build_prediction_sa7(home_id: int, away_id: int, match_key: str | None = None) -> dict:
    """Build prediction using SportApi7 team last-events data. Cached per (home,away)."""
    cache_id = match_key or f"sa7-{home_id}-{away_id}"
    doc = await db.prediction_cache.find_one({"_id": cache_id})
    if doc and doc.get("expires_at") and doc["expires_at"] > datetime.utcnow():
        return doc["data"]
    try:
        home_data = await sa7.team_last(db, home_id)
        away_data = await sa7.team_last(db, away_id)
    except Exception as e:
        logger.warning(f"sa7 team fetch failed: {e}")
        home_data = {"events": []}
        away_data = {"events": []}
    home_matches = sa7.sa7_events_to_predictor_format(home_data.get("events", []))
    away_matches = sa7.sa7_events_to_predictor_format(away_data.get("events", []))
    pred = predict(home_matches, away_matches, home_id, away_id)
    await db.prediction_cache.update_one(
        {"_id": cache_id},
        {"$set": {"data": pred, "expires_at": datetime.utcnow() + timedelta(minutes=30)}},
        upsert=True,
    )
    return pred


async def _get_current_season(tid: int) -> int | None:
    """Fetch the latest season ID for a tournament (cached)."""
    try:
        data = await sa7.tournament_seasons(db, tid)
        seasons = data.get("seasons") or []
        if seasons:
            return seasons[0].get("id")
    except Exception:
        pass
    # Fallback to hard-coded (no longer stored)
    return None


@api_router.get("/global/predictions/tournament/{tid}")
async def global_predictions_tournament(tid: int, season: int | None = None, limit: int = 10):
    """Upcoming matches for a SportApi7 tournament with AI predictions computed from real team form."""
    if season is None:
        season = await _get_current_season(tid)
    if not season:
        return {"count": 0, "matches": [], "error": "Season data unavailable (API quota may be reached)"}
    # Get current round
    matches = []
    try:
        rounds_data = await sa7.tournament_rounds(db, tid, season)
        current_round = (rounds_data.get("currentRound") or {}).get("round") or 1
    except Exception:
        current_round = 1
    # Try current round and up to 2 next rounds
    for r in [current_round, current_round + 1, current_round + 2]:
        try:
            data = await sa7.events_round(db, tid, season, r)
            for e in data.get("events", []):
                st = ((e.get("status") or {}).get("type") or "").lower()
                if st in ("notstarted", "inprogress"):
                    matches.append(e)
        except Exception:
            continue
        if len(matches) >= limit:
            break
    matches = matches[:limit]
    out = []
    for e in matches:
        home_id = (e.get("homeTeam") or {}).get("id")
        away_id = (e.get("awayTeam") or {}).get("id")
        pred = None
        if home_id and away_id:
            try:
                pred = await _build_prediction_sa7(home_id, away_id, match_key=f"sa7-event-{e.get('id')}")
            except Exception as ex:
                logger.warning(f"sa7 pred failed: {ex}")
        norm = sa7.normalize_event(e)
        norm["prediction"] = pred
        out.append(norm)
    return {"count": len(out), "matches": out}


@api_router.get("/global/predictions/live")
async def global_predictions_live(limit: int = 12):
    """Live matches worldwide with AI predictions attached."""
    data = await sa7.live_events(db)
    events = data.get("events") or []
    if data.get("error"):
        return {"count": 0, "matches": [], "error": "API quota reached"}
    # Prioritise major tournaments
    priority_ids = {t["id"] for t in sa7.TOURNAMENTS}
    events.sort(key=lambda e: 0 if ((e.get("tournament", {}).get("uniqueTournament") or {}).get("id") in priority_ids) else 1)
    events = events[:limit]
    out = []
    for e in events:
        home_id = (e.get("homeTeam") or {}).get("id")
        away_id = (e.get("awayTeam") or {}).get("id")
        pred = None
        if home_id and away_id:
            try:
                pred = await _build_prediction_sa7(home_id, away_id, match_key=f"sa7-event-{e.get('id')}")
            except Exception as ex:
                logger.warning(f"live pred failed: {ex}")
        norm = sa7.normalize_event(e)
        norm["prediction"] = pred
        out.append(norm)
    return {"count": len(out), "matches": out}


@api_router.get("/global/predictions/upcoming")
async def global_predictions_upcoming(limit: int = 12):
    """Aggregate upcoming SportApi7 predictions across our curated tournaments."""
    out = []
    per_league = max(1, limit // 6)
    for t in sa7.TOURNAMENTS[:8]:  # cover top 8 tournaments
        try:
            data = await global_predictions_tournament(t["id"], None, per_league)
            out.extend(data.get("matches", []))
        except Exception as ex:
            logger.warning(f"skipping {t['name']}: {ex}")
        if len(out) >= limit:
            break
    # Sort by kickoff time
    out.sort(key=lambda m: m.get("utcDate") or "")
    return {"count": len(out), "matches": out[:limit]}


@api_router.get("/apif/leagues")
async def apif_leagues():
    return {"count": len(sa7.TOURNAMENTS), "tournaments": sa7.TOURNAMENTS}


@api_router.get("/apif/fixtures")
async def apif_fixtures(date: str):
    # SportApi7 doesn't have date-based schedules; return live + curated tournaments' recent events
    data = await sa7.live_events(db)
    events = data.get("events") or []
    return {"count": len(events), "matches": [sa7.normalize_event(e) for e in events]}


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
async def predictions_upcoming(days: int = 14, limit: int = 24):
    limit = min(limit, 30)
    days = min(days, 30)
    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    data = await fa.get_matches_for_date_range(db, date_from, date_to)
    matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")]
    # Sort by date so users see soonest first
    matches.sort(key=lambda m: m.get("utcDate") or "")
    matches = matches[:limit]
    out = []
    for m in matches:
        pred = await _build_prediction(m)
        out.append(_serialize_match(m, pred))
    return {"count": len(out), "matches": out}


@api_router.get("/predictions/bet-of-the-day")
async def bet_of_the_day():
    """Bet of the Day - returns EVERY match whose best_bet confidence exceeds
    BET_CONFIDENCE_THRESHOLD, ranked highest to lowest, capped at MAX_BETS_PER_DAY.
    (Underlying 1X2 / Over-Under / BTTS math is unchanged - only how many
    results get surfaced has changed.)"""
    data = await fa.get_today_matches(db)
    matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")]
    candidates = []
    for m in matches[:6]:
        pred = await _build_prediction(m)
        candidates.append({"match": m, "prediction": pred})
    picks = select_bets_of_day(candidates)
    if not picks:
        # Widen the window to the next 3 days if today has no qualifying picks.
        date_from = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d")
        data = await fa.get_matches_for_date_range(db, date_from, date_to)
        matches = [m for m in data.get("matches", []) if m.get("status") in ("TIMED", "SCHEDULED")][:10]
        candidates = []
        for m in matches:
            pred = await _build_prediction(m)
            candidates.append({"match": m, "prediction": pred})
        picks = select_bets_of_day(candidates)
    return {
        "count": len(picks),
        "threshold": BET_CONFIDENCE_THRESHOLD,
        "picks": [_serialize_match(c["match"], c["prediction"]) for c in picks],
    }


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
