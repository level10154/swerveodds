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
