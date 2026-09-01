"""NerdyStats backend regression tests (5-step change round).

Covers:
- Shared endpoints kept after StatsHub removal (/api/competitions, /api/standings/{code})
- Bet of the Day new response shape {count, threshold, picks: []}
- World endpoints (5DollarFootballAPI adapter) graceful degradation with invalid key
- predictor.select_bets_of_day() unit behaviour
"""
import os
import sys
import time

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


# --- health / shared endpoints (must survive StatsHub removal) ---
class TestHealthAndShared:
    def test_root(self, client):
        r = client.get(f"{API}/", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("status") == "ok"

    def test_competitions(self, client):
        r = client.get(f"{API}/competitions", timeout=60)
        assert r.status_code == 200, r.text[:300]
        comps = r.json().get("competitions")
        assert isinstance(comps, list) and len(comps) > 0
        assert "code" in comps[0] and "name" in comps[0]

    def test_standings_shared_endpoint(self, client):
        r = client.get(f"{API}/standings/PL", timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "table" in data or "standings" in data


# --- Bet of the Day: new multi-pick contract (STEP 3) ---
class TestBetOfTheDay:
    def test_shape_and_threshold(self, client):
        start = time.time()
        r = client.get(f"{API}/predictions/bet-of-the-day", timeout=120)
        elapsed = time.time() - start
        print(f"bet-of-the-day took {elapsed:.1f}s")
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert set(["count", "threshold", "picks"]).issubset(data.keys()), data.keys()
        assert data["threshold"] == 60
        assert isinstance(data["picks"], list)
        assert data["count"] == len(data["picks"])
        assert data["count"] <= 8, "MAX_BETS_PER_DAY cap violated"
        # no single-match legacy fields at top level
        assert "homeTeam" not in data and "prediction" not in data

    def test_picks_ranked_and_above_threshold(self, client):
        r = client.get(f"{API}/predictions/bet-of-the-day", timeout=120)
        assert r.status_code == 200
        picks = r.json()["picks"]
        if not picks:
            pytest.skip("no qualifying picks right now (graceful empty state)")
        confs = []
        for p in picks:
            assert "prediction" in p, p.keys()
            bb = p["prediction"]["best_bet"]
            assert bb["confidence"] > 60, f"pick below threshold: {bb}"
            assert p["homeTeam"]["name"] and p["awayTeam"]["name"]
            confs.append(bb["confidence"])
        assert confs == sorted(confs, reverse=True), f"picks not ranked desc: {confs}"

    def test_no_mongo_objectid_leak(self, client):
        r = client.get(f"{API}/predictions/bet-of-the-day", timeout=120)
        assert "_id" not in r.text


# --- World endpoints / 5DollarFootballAPI graceful degradation (STEP 4) ---
class TestWorldEndpoints:
    def test_world_leagues_sources(self, client):
        r = client.get(f"{API}/world/leagues", timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        leagues = data["leagues"]
        assert data["count"] == len(leagues)
        sources = {l["source"] for l in leagues}
        assert "thesportsdb" not in sources, f"legacy source still present: {sources}"
        assert "fivedollarfootball" in sources
        assert "football-data" in sources
        fd = [l for l in leagues if l["source"] == "fivedollarfootball"]
        assert len(fd) > 0
        assert all(l["id"].startswith("fivedollar-") for l in fd)
        assert all(l["emblem"] for l in fd), "generated avatar badge missing"

    def test_world_matches_today_graceful(self, client):
        start = time.time()
        r = client.get(f"{API}/world/matches/today", timeout=120)
        elapsed = time.time() - start
        print(f"world/matches/today took {elapsed:.1f}s")
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data["matches"], list)
        assert data["count"] == len(data["matches"])

    def test_world_league_next_graceful(self, client):
        r = client.get(f"{API}/world/league/fivedollar-MLS/next", timeout=120)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["league"]["name"] == "Major League Soccer"
        assert "5DollarFootballAPI" in data["league"]["description"]
        assert isinstance(data["upcoming"], list)
        assert isinstance(data["recent"], list)

    def test_world_league_table_graceful(self, client):
        r = client.get(f"{API}/world/league/fivedollar-MLS/table", timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["table"] == []
        assert data["league"]["code"] if "code" in data["league"] else True

    def test_world_league_bad_ref(self, client):
        r = client.get(f"{API}/world/league/thesportsdb-4346/next", timeout=60)
        assert r.status_code == 400, r.text[:200]

    def test_world_league_unknown_code(self, client):
        r = client.get(f"{API}/world/league/fivedollar-ZZZ/next", timeout=60)
        assert r.status_code == 404, r.text[:200]


# --- Predictions endpoints used by the rolling 7-day tabs (STEP 2) ---
class TestPredictions:
    def test_predictions_upcoming_contract(self, client):
        r = client.get(f"{API}/predictions/upcoming?days=7&limit=24", timeout=180)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data["matches"], list)
        assert data["count"] == len(data["matches"])
        if data["matches"]:
            m = data["matches"][0]
            assert m["utcDate"] and m["homeTeam"]["name"]
            assert "prediction" in m

    def test_matches_range_contract(self, client):
        from datetime import datetime, timedelta
        d0 = datetime.utcnow().strftime("%Y-%m-%d")
        d1 = (datetime.utcnow() + timedelta(days=6)).strftime("%Y-%m-%d")
        r = client.get(f"{API}/matches/range?date_from={d0}&date_to={d1}", timeout=180)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json()["matches"], list)

    def test_matches_today(self, client):
        r = client.get(f"{API}/matches/today", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json()["matches"], list)


# --- predictor unit tests (STEP 3 logic) ---
class TestSelectorUnit:
    def _cand(self, conf):
        return {"match": {"id": conf}, "prediction": {"best_bet": {"confidence": conf}}}

    def test_threshold_and_ranking_and_cap(self):
        from predictor import select_bets_of_day, BET_CONFIDENCE_THRESHOLD, MAX_BETS_PER_DAY
        assert BET_CONFIDENCE_THRESHOLD == 60
        assert MAX_BETS_PER_DAY == 8
        cands = [self._cand(c) for c in [55, 60, 61, 99, 70, 80, 85, 90, 95, 62, 63, 64]]
        out = select_bets_of_day(cands)
        assert len(out) == 8
        confs = [c["prediction"]["best_bet"]["confidence"] for c in out]
        assert confs == sorted(confs, reverse=True)
        assert all(c > 60 for c in confs), confs

    def test_empty_input(self):
        from predictor import select_bets_of_day
        assert select_bets_of_day([]) == []
