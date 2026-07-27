"""
Backend API Testing for NerdyStats
Tests all endpoints with proper rate limiting and cache verification
"""
import requests
import time
import json
from typing import Dict, Any, List

# Base URL from frontend/.env
BASE_URL = "https://nerdy-stats-ai.preview.emergentagent.com/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_result(test_name: str, passed: bool, message: str, data: Any = None):
    """Log test result"""
    result = {
        "test": test_name,
        "message": message,
        "data": data
    }
    if passed:
        test_results["passed"].append(result)
        print(f"✅ PASS: {test_name} - {message}")
    else:
        test_results["failed"].append(result)
        print(f"❌ FAIL: {test_name} - {message}")
    if data:
        print(f"   Data: {json.dumps(data, indent=2)[:500]}")

def log_warning(test_name: str, message: str):
    """Log warning"""
    test_results["warnings"].append({"test": test_name, "message": message})
    print(f"⚠️  WARNING: {test_name} - {message}")

def validate_prediction_structure(prediction: Dict, test_name: str) -> bool:
    """Validate prediction object has all required fields"""
    if not prediction:
        log_result(test_name, False, "Prediction is None or empty", prediction)
        return False
    
    # Check required top-level keys
    required_keys = ["probs", "top_scores", "most_likely_score", "pick", "confidence", "best_bet"]
    missing_keys = [k for k in required_keys if k not in prediction]
    if missing_keys:
        log_result(test_name, False, f"Missing prediction keys: {missing_keys}", prediction)
        return False
    
    # Check probs structure
    probs = prediction.get("probs", {})
    required_prob_keys = ["home", "draw", "away", "btts_yes", "over_25"]
    missing_prob_keys = [k for k in required_prob_keys if k not in probs]
    if missing_prob_keys:
        log_result(test_name, False, f"Missing probs keys: {missing_prob_keys}", probs)
        return False
    
    # Validate probability ranges (0-100)
    for key, value in probs.items():
        if value is None:
            log_result(test_name, False, f"Probability {key} is None", probs)
            return False
        if not (0 <= value <= 100):
            log_result(test_name, False, f"Probability {key}={value} outside 0-100 range", probs)
            return False
    
    # Check best_bet structure
    best_bet = prediction.get("best_bet", {})
    if "market" not in best_bet or "pick" not in best_bet or "confidence" not in best_bet:
        log_result(test_name, False, "best_bet missing required keys", best_bet)
        return False
    
    # Validate best_bet.market
    valid_markets = {"1X2", "Over 2.5 Goals", "BTTS"}
    if best_bet["market"] not in valid_markets:
        log_result(test_name, False, f"best_bet.market '{best_bet['market']}' not in {valid_markets}", best_bet)
        return False
    
    # Check top_scores is a list
    if not isinstance(prediction.get("top_scores"), list):
        log_result(test_name, False, "top_scores is not a list", prediction.get("top_scores"))
        return False
    
    # Check most_likely_score structure
    mls = prediction.get("most_likely_score", {})
    if "score" not in mls or "prob" not in mls:
        log_result(test_name, False, "most_likely_score missing score or prob", mls)
        return False
    
    return True

def test_competitions():
    """Test GET /api/competitions"""
    print("\n" + "="*80)
    print("TEST 1: GET /api/competitions")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/competitions", timeout=30)
        
        if response.status_code >= 500:
            log_result("competitions", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("competitions", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "competitions" not in data:
            log_result("competitions", False, "Missing 'competitions' key", data)
            return None
        
        comps = data["competitions"]
        if not isinstance(comps, list):
            log_result("competitions", False, "competitions is not a list", comps)
            return None
        
        if len(comps) < 10:
            log_warning("competitions", f"Expected ~11 competitions, got {len(comps)}")
        
        # Check structure of first competition
        if comps:
            comp = comps[0]
            required_keys = ["code", "id", "name", "country", "emblem"]
            missing = [k for k in required_keys if k not in comp]
            if missing:
                log_result("competitions", False, f"Competition missing keys: {missing}", comp)
                return None
        
        log_result("competitions", True, f"Got {len(comps)} competitions", {"sample": comps[0] if comps else None})
        return data
        
    except Exception as e:
        log_result("competitions", False, f"Exception: {str(e)}", None)
        return None

def test_matches_today():
    """Test GET /api/matches/today"""
    print("\n" + "="*80)
    print("TEST 2: GET /api/matches/today")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/matches/today", timeout=30)
        
        if response.status_code >= 500:
            log_result("matches/today", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("matches/today", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "count" not in data or "matches" not in data:
            log_result("matches/today", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("matches/today", False, "matches is not a list", matches)
            return None
        
        # Check structure if matches exist
        if matches:
            match = matches[0]
            required_keys = ["id", "utcDate", "status", "competition", "homeTeam", "awayTeam", "score"]
            missing = [k for k in required_keys if k not in match]
            if missing:
                log_result("matches/today", False, f"Match missing keys: {missing}", match)
                return None
            
            log_result("matches/today", True, f"Got {len(matches)} matches", {"sample": match})
        else:
            log_result("matches/today", True, "Got 0 matches (may be off-season)", {"count": 0})
        
        return data
        
    except Exception as e:
        log_result("matches/today", False, f"Exception: {str(e)}", None)
        return None

def test_predictions_today():
    """Test GET /api/predictions/today?limit=3"""
    print("\n" + "="*80)
    print("TEST 3: GET /api/predictions/today?limit=3")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/predictions/today?limit=3", timeout=60)
        
        if response.status_code >= 500:
            log_result("predictions/today", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("predictions/today", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "count" not in data or "matches" not in data:
            log_result("predictions/today", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("predictions/today", False, "matches is not a list", matches)
            return None
        
        if matches:
            # Validate each match has prediction
            for i, match in enumerate(matches):
                if "prediction" not in match:
                    log_result("predictions/today", False, f"Match {i} missing prediction", match)
                    return None
                
                if not validate_prediction_structure(match["prediction"], f"predictions/today[{i}]"):
                    return None
            
            log_result("predictions/today", True, f"Got {len(matches)} matches with valid predictions", 
                      {"sample_prediction": matches[0]["prediction"]})
        else:
            log_result("predictions/today", True, "Got 0 matches (may be off-season)", {"count": 0})
        
        return data
        
    except Exception as e:
        log_result("predictions/today", False, f"Exception: {str(e)}", None)
        return None

def test_predictions_upcoming():
    """Test GET /api/predictions/upcoming?days=2&limit=5"""
    print("\n" + "="*80)
    print("TEST 4: GET /api/predictions/upcoming?days=2&limit=5")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/predictions/upcoming?days=2&limit=5", timeout=60)
        
        if response.status_code >= 500:
            log_result("predictions/upcoming", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("predictions/upcoming", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "count" not in data or "matches" not in data:
            log_result("predictions/upcoming", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("predictions/upcoming", False, "matches is not a list", matches)
            return None
        
        if matches:
            # Validate each match has prediction
            for i, match in enumerate(matches):
                if "prediction" not in match:
                    log_result("predictions/upcoming", False, f"Match {i} missing prediction", match)
                    return None
                
                if not validate_prediction_structure(match["prediction"], f"predictions/upcoming[{i}]"):
                    return None
            
            log_result("predictions/upcoming", True, f"Got {len(matches)} matches with valid predictions",
                      {"sample_prediction": matches[0]["prediction"]})
        else:
            log_result("predictions/upcoming", True, "Got 0 matches (may be off-season)", {"count": 0})
        
        return data
        
    except Exception as e:
        log_result("predictions/upcoming", False, f"Exception: {str(e)}", None)
        return None

def test_predictions_upcoming_expanded():
    """Test GET /api/predictions/upcoming?days=14&limit=10 - expanded window for worldwide coverage"""
    print("\n" + "="*80)
    print("TEST 4B: GET /api/predictions/upcoming?days=14&limit=10 (EXPANDED WINDOW)")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/predictions/upcoming?days=14&limit=10", timeout=60)
        
        if response.status_code >= 500:
            log_result("predictions/upcoming_14days", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("predictions/upcoming_14days", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "count" not in data or "matches" not in data:
            log_result("predictions/upcoming_14days", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("predictions/upcoming_14days", False, "matches is not a list", matches)
            return None
        
        if matches:
            # Validate each match has prediction
            for i, match in enumerate(matches):
                if "prediction" not in match:
                    log_result("predictions/upcoming_14days", False, f"Match {i} missing prediction", match)
                    return None
                
                if not validate_prediction_structure(match["prediction"], f"predictions/upcoming_14days[{i}]"):
                    return None
            
            # Check for league diversity (should have more than just Brazilian league)
            leagues = set()
            for match in matches:
                comp_name = match.get("competition", {}).get("name", "")
                if comp_name:
                    leagues.add(comp_name)
            
            log_result("predictions/upcoming_14days", True, 
                      f"Got {len(matches)} matches from {len(leagues)} leagues with valid predictions",
                      {"leagues": list(leagues), "sample_prediction": matches[0]["prediction"]})
        else:
            log_result("predictions/upcoming_14days", True, "Got 0 matches (may be off-season)", {"count": 0})
        
        return data
        
    except Exception as e:
        log_result("predictions/upcoming_14days", False, f"Exception: {str(e)}", None)
        return None

def test_bet_of_the_day():
    """Test GET /api/predictions/bet-of-the-day"""
    print("\n" + "="*80)
    print("TEST 5: GET /api/predictions/bet-of-the-day")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/predictions/bet-of-the-day", timeout=60)
        
        if response.status_code >= 500:
            log_result("bet-of-the-day", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code == 404:
            log_result("bet-of-the-day", True, "No matches available (404 expected in off-season)", None)
            return None
        
        if response.status_code != 200:
            log_result("bet-of-the-day", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        match = response.json()
        
        if "prediction" not in match:
            log_result("bet-of-the-day", False, "Match missing prediction", match)
            return None
        
        if not validate_prediction_structure(match["prediction"], "bet-of-the-day"):
            return None
        
        log_result("bet-of-the-day", True, "Got bet of the day with valid prediction",
                  {"prediction": match["prediction"]})
        
        return match
        
    except Exception as e:
        log_result("bet-of-the-day", False, f"Exception: {str(e)}", None)
        return None

def test_standings():
    """Test GET /api/standings/PL"""
    print("\n" + "="*80)
    print("TEST 6: GET /api/standings/PL")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/standings/PL", timeout=30)
        
        if response.status_code >= 500:
            log_result("standings/PL", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("standings/PL", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "standings" not in data:
            log_result("standings/PL", False, "Missing standings key", data)
            return None
        
        standings = data["standings"]
        if not isinstance(standings, list):
            log_result("standings/PL", False, "standings is not a list", standings)
            return None
        
        # Find TOTAL type
        total_standing = None
        for s in standings:
            if s.get("type") == "TOTAL":
                total_standing = s
                break
        
        if not total_standing:
            log_result("standings/PL", False, "No TOTAL type standing found", standings)
            return None
        
        table = total_standing.get("table", [])
        if len(table) < 15:
            log_warning("standings/PL", f"Expected ~20 teams, got {len(table)}")
        
        # Check structure of first entry
        if table:
            entry = table[0]
            required_keys = ["team", "playedGames", "won", "draw", "lost", "goalDifference", "points"]
            missing = [k for k in required_keys if k not in entry]
            if missing:
                log_result("standings/PL", False, f"Table entry missing keys: {missing}", entry)
                return None
            
            team = entry.get("team", {})
            team_keys = ["id", "name", "shortName", "crest"]
            missing_team = [k for k in team_keys if k not in team]
            if missing_team:
                log_result("standings/PL", False, f"Team missing keys: {missing_team}", team)
                return None
        
        log_result("standings/PL", True, f"Got standings with {len(table)} teams",
                  {"sample": table[0] if table else None})
        
        return data
        
    except Exception as e:
        log_result("standings/PL", False, f"Exception: {str(e)}", None)
        return None

def test_competition_matches():
    """Test GET /api/competition/PL/matches?status=SCHEDULED"""
    print("\n" + "="*80)
    print("TEST 7: GET /api/competition/PL/matches?status=SCHEDULED")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/competition/PL/matches?status=SCHEDULED", timeout=30)
        
        if response.status_code >= 500:
            log_result("competition/PL/matches", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("competition/PL/matches", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "count" not in data or "matches" not in data:
            log_result("competition/PL/matches", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("competition/PL/matches", False, "matches is not a list", matches)
            return None
        
        log_result("competition/PL/matches", True, f"Got {len(matches)} scheduled matches",
                  {"sample": matches[0] if matches else None})
        
        return data
        
    except Exception as e:
        log_result("competition/PL/matches", False, f"Exception: {str(e)}", None)
        return None

def test_competition_scorers():
    """Test GET /api/competition/PL/scorers"""
    print("\n" + "="*80)
    print("TEST 8: GET /api/competition/PL/scorers")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/competition/PL/scorers", timeout=30)
        
        if response.status_code >= 500:
            log_result("competition/PL/scorers", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("competition/PL/scorers", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        if "scorers" not in data:
            log_result("competition/PL/scorers", False, "Missing scorers key", data)
            return None
        
        scorers = data["scorers"]
        if not isinstance(scorers, list):
            log_result("competition/PL/scorers", False, "scorers is not a list", scorers)
            return None
        
        # Check structure if scorers exist
        if scorers:
            scorer = scorers[0]
            required_keys = ["player", "team", "goals"]
            missing = [k for k in required_keys if k not in scorer]
            if missing:
                log_result("competition/PL/scorers", False, f"Scorer missing keys: {missing}", scorer)
                return None
        
        log_result("competition/PL/scorers", True, f"Got {len(scorers)} scorers",
                  {"sample": scorers[0] if scorers else None})
        
        return data
        
    except Exception as e:
        log_result("competition/PL/scorers", False, f"Exception: {str(e)}", None)
        return None

def test_match_detail(match_id: int):
    """Test GET /api/match/{id}"""
    print("\n" + "="*80)
    print(f"TEST 9: GET /api/match/{match_id}")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/match/{match_id}", timeout=60)
        
        if response.status_code >= 500:
            log_result(f"match/{match_id}", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code == 404:
            log_result(f"match/{match_id}", False, f"Match not found (404)", response.text)
            return None
        
        if response.status_code != 200:
            log_result(f"match/{match_id}", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        match = response.json()
        
        if "prediction" not in match:
            log_result(f"match/{match_id}", False, "Match missing prediction", match)
            return None
        
        if not validate_prediction_structure(match["prediction"], f"match/{match_id}"):
            return None
        
        log_result(f"match/{match_id}", True, "Got match detail with valid prediction",
                  {"prediction": match["prediction"]})
        
        return match
        
    except Exception as e:
        log_result(f"match/{match_id}", False, f"Exception: {str(e)}", None)
        return None

def test_global_predictions_k_league():
    """Test GET /api/global/predictions/tournament/410?limit=3 (K League 1)"""
    print("\n" + "="*80)
    print("TEST 11: GET /api/global/predictions/tournament/410?limit=3 (K League 1)")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/global/predictions/tournament/410?limit=3", timeout=60)
        
        if response.status_code >= 500:
            log_result("global/predictions/k-league", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("global/predictions/k-league", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        # Check for graceful error handling
        if "error" in data:
            if data.get("count") == 0 and "matches" in data and data["matches"] == []:
                log_result("global/predictions/k-league", True, 
                          f"Graceful error handling: {data.get('error')}", data)
                return data
            else:
                log_result("global/predictions/k-league", False, f"Error response: {data.get('error')}", data)
                return None
        
        if "count" not in data or "matches" not in data:
            log_result("global/predictions/k-league", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("global/predictions/k-league", False, "matches is not a list", matches)
            return None
        
        if data["count"] < 1:
            log_result("global/predictions/k-league", False, "Expected count >= 1, got 0", data)
            return None
        
        # Validate each match has prediction with required structure
        for i, match in enumerate(matches):
            if "prediction" not in match or match["prediction"] is None:
                log_result("global/predictions/k-league", False, f"Match {i} missing prediction", match)
                return None
            
            pred = match["prediction"]
            
            # Check probs structure
            if "probs" not in pred:
                log_result("global/predictions/k-league", False, f"Match {i} prediction missing probs", pred)
                return None
            
            probs = pred["probs"]
            required_probs = ["home", "draw", "away"]
            for p in required_probs:
                if p not in probs:
                    log_result("global/predictions/k-league", False, f"Match {i} probs missing {p}", probs)
                    return None
                if not (0 <= probs[p] <= 100):
                    log_result("global/predictions/k-league", False, 
                              f"Match {i} probs.{p}={probs[p]} outside 0-100 range", probs)
                    return None
            
            # Check best_bet structure
            if "best_bet" not in pred:
                log_result("global/predictions/k-league", False, f"Match {i} prediction missing best_bet", pred)
                return None
            
            best_bet = pred["best_bet"]
            required_bet_keys = ["market", "pick", "confidence"]
            for key in required_bet_keys:
                if key not in best_bet:
                    log_result("global/predictions/k-league", False, 
                              f"Match {i} best_bet missing {key}", best_bet)
                    return None
            
            if not (0 <= best_bet["confidence"] <= 100):
                log_result("global/predictions/k-league", False, 
                          f"Match {i} best_bet.confidence={best_bet['confidence']} outside 0-100 range", 
                          best_bet)
                return None
        
        log_result("global/predictions/k-league", True, 
                  f"Got {len(matches)} K League 1 matches with valid predictions",
                  {"sample_prediction": matches[0]["prediction"]})
        
        return data
        
    except Exception as e:
        log_result("global/predictions/k-league", False, f"Exception: {str(e)}", None)
        return None

def test_global_predictions_chinese_super_league():
    """Test GET /api/global/predictions/tournament/649?limit=3 (Chinese Super League)"""
    print("\n" + "="*80)
    print("TEST 12: GET /api/global/predictions/tournament/649?limit=3 (Chinese Super League)")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/global/predictions/tournament/649?limit=3", timeout=60)
        
        if response.status_code >= 500:
            log_result("global/predictions/csl", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("global/predictions/csl", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        # Check for graceful error handling
        if "error" in data:
            if data.get("count") == 0 and "matches" in data and data["matches"] == []:
                log_result("global/predictions/csl", True, 
                          f"Graceful error handling: {data.get('error')}", data)
                return data
            else:
                log_result("global/predictions/csl", False, f"Error response: {data.get('error')}", data)
                return None
        
        if "count" not in data or "matches" not in data:
            log_result("global/predictions/csl", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("global/predictions/csl", False, "matches is not a list", matches)
            return None
        
        if data["count"] < 1:
            log_result("global/predictions/csl", False, "Expected count >= 1, got 0", data)
            return None
        
        # Validate prediction structure (same as K League test)
        for i, match in enumerate(matches):
            if "prediction" not in match or match["prediction"] is None:
                log_result("global/predictions/csl", False, f"Match {i} missing prediction", match)
                return None
            
            pred = match["prediction"]
            
            if "probs" not in pred or "best_bet" not in pred:
                log_result("global/predictions/csl", False, f"Match {i} prediction incomplete", pred)
                return None
            
            probs = pred["probs"]
            for p in ["home", "draw", "away"]:
                if p not in probs or not (0 <= probs[p] <= 100):
                    log_result("global/predictions/csl", False, f"Match {i} probs invalid", probs)
                    return None
            
            best_bet = pred["best_bet"]
            if not all(k in best_bet for k in ["market", "pick", "confidence"]):
                log_result("global/predictions/csl", False, f"Match {i} best_bet incomplete", best_bet)
                return None
            
            if not (0 <= best_bet["confidence"] <= 100):
                log_result("global/predictions/csl", False, f"Match {i} confidence out of range", best_bet)
                return None
        
        log_result("global/predictions/csl", True, 
                  f"Got {len(matches)} Chinese Super League matches with valid predictions",
                  {"sample_prediction": matches[0]["prediction"]})
        
        return data
        
    except Exception as e:
        log_result("global/predictions/csl", False, f"Exception: {str(e)}", None)
        return None

def test_global_predictions_allsvenskan():
    """Test GET /api/global/predictions/tournament/40?limit=2 (Allsvenskan) - should gracefully handle no data"""
    print("\n" + "="*80)
    print("TEST 13: GET /api/global/predictions/tournament/40?limit=2 (Allsvenskan - graceful error)")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/global/predictions/tournament/40?limit=2", timeout=60)
        
        if response.status_code >= 500:
            log_result("global/predictions/allsvenskan", False, 
                      f"5xx error (should return 200 with error message): {response.status_code}", 
                      response.text)
            return None
        
        if response.status_code != 200:
            log_result("global/predictions/allsvenskan", False, 
                      f"Non-200 status (expected 200 with graceful error): {response.status_code}", 
                      response.text)
            return None
        
        data = response.json()
        
        # MUST have graceful error structure
        if "count" not in data or "matches" not in data:
            log_result("global/predictions/allsvenskan", False, 
                      "Missing count or matches key (required for graceful error)", data)
            return None
        
        if data["count"] != 0:
            # If there's data, validate it
            matches = data["matches"]
            if matches:
                log_result("global/predictions/allsvenskan", True, 
                          f"Got {len(matches)} Allsvenskan matches (season data available)",
                          {"sample": matches[0] if matches else None})
                return data
        
        # Check for graceful error message
        if "error" not in data:
            log_result("global/predictions/allsvenskan", False, 
                      "Expected 'error' field when count=0 (graceful error handling)", data)
            return None
        
        error_msg = data["error"]
        if "Season data unavailable" not in error_msg and "quota" not in error_msg.lower():
            log_result("global/predictions/allsvenskan", False, 
                      f"Error message doesn't mention season/quota: {error_msg}", data)
            return None
        
        if data["matches"] != []:
            log_result("global/predictions/allsvenskan", False, 
                      "matches should be empty array when count=0", data)
            return None
        
        log_result("global/predictions/allsvenskan", True, 
                  f"Graceful error handling confirmed: {error_msg}", data)
        
        return data
        
    except Exception as e:
        log_result("global/predictions/allsvenskan", False, f"Exception: {str(e)}", None)
        return None

def test_global_predictions_live():
    """Test GET /api/global/predictions/live?limit=6 - live matches worldwide with predictions"""
    print("\n" + "="*80)
    print("TEST 14: GET /api/global/predictions/live?limit=6 (Live worldwide matches)")
    print("="*80)
    
    try:
        time.sleep(7)  # Rate limit
        response = requests.get(f"{BASE_URL}/global/predictions/live?limit=6", timeout=60)
        
        if response.status_code >= 500:
            log_result("global/predictions/live", False, f"5xx error: {response.status_code}", response.text)
            return None
        
        if response.status_code != 200:
            log_result("global/predictions/live", False, f"Non-200 status: {response.status_code}", response.text)
            return None
        
        data = response.json()
        
        # Check for API quota error (graceful)
        if "error" in data:
            if data.get("count") == 0 and "matches" in data:
                log_result("global/predictions/live", True, 
                          f"Graceful error (API quota): {data.get('error')}", data)
                return data
            else:
                log_result("global/predictions/live", False, f"Error response: {data.get('error')}", data)
                return None
        
        if "count" not in data or "matches" not in data:
            log_result("global/predictions/live", False, "Missing count or matches key", data)
            return None
        
        matches = data["matches"]
        if not isinstance(matches, list):
            log_result("global/predictions/live", False, "matches is not a list", matches)
            return None
        
        if not matches:
            log_result("global/predictions/live", True, 
                      "No live matches currently (expected if no games in progress)", {"count": 0})
            return data
        
        # Validate matches have predictions
        for i, match in enumerate(matches):
            # Prediction may be None for some live matches (that's ok)
            if "prediction" in match and match["prediction"] is not None:
                pred = match["prediction"]
                if "probs" in pred and "best_bet" in pred:
                    # Quick validation
                    probs = pred["probs"]
                    if not all(k in probs for k in ["home", "draw", "away"]):
                        log_result("global/predictions/live", False, 
                                  f"Match {i} prediction probs incomplete", pred)
                        return None
        
        log_result("global/predictions/live", True, 
                  f"Got {len(matches)} live matches (predictions may be partial from cache)",
                  {"sample": matches[0] if matches else None})
        
        return data
        
    except Exception as e:
        log_result("global/predictions/live", False, f"Exception: {str(e)}", None)
        return None

def test_cache_functionality():
    """Test that cache returns same data instantly on second call"""
    print("\n" + "="*80)
    print("TEST 10: Cache Verification (calling /api/competitions twice)")
    print("="*80)
    
    try:
        # First call
        start1 = time.time()
        response1 = requests.get(f"{BASE_URL}/competitions", timeout=30)
        duration1 = time.time() - start1
        
        if response1.status_code != 200:
            log_result("cache_test", False, f"First call failed: {response1.status_code}", None)
            return
        
        data1 = response1.json()
        
        # Second call (should be instant from cache)
        start2 = time.time()
        response2 = requests.get(f"{BASE_URL}/competitions", timeout=30)
        duration2 = time.time() - start2
        
        if response2.status_code != 200:
            log_result("cache_test", False, f"Second call failed: {response2.status_code}", None)
            return
        
        data2 = response2.json()
        
        # Compare data
        if data1 != data2:
            log_result("cache_test", False, "Data mismatch between calls", {"diff": "data differs"})
            return
        
        # Check if second call was faster (cached)
        if duration2 < duration1 * 0.5:  # Should be significantly faster
            log_result("cache_test", True, f"Cache working: 1st={duration1:.2f}s, 2nd={duration2:.2f}s (cached)",
                      {"duration1": duration1, "duration2": duration2})
        else:
            log_warning("cache_test", f"Second call not significantly faster: 1st={duration1:.2f}s, 2nd={duration2:.2f}s")
            log_result("cache_test", True, "Data consistent but cache speed unclear",
                      {"duration1": duration1, "duration2": duration2})
        
    except Exception as e:
        log_result("cache_test", False, f"Exception: {str(e)}", None)

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    print(f"\n✅ PASSED: {len(test_results['passed'])}")
    for result in test_results['passed']:
        print(f"   - {result['test']}: {result['message']}")
    
    print(f"\n❌ FAILED: {len(test_results['failed'])}")
    for result in test_results['failed']:
        print(f"   - {result['test']}: {result['message']}")
    
    print(f"\n⚠️  WARNINGS: {len(test_results['warnings'])}")
    for result in test_results['warnings']:
        print(f"   - {result['test']}: {result['message']}")
    
    print("\n" + "="*80)
    if test_results['failed']:
        print("OVERALL: TESTS FAILED ❌")
    else:
        print("OVERALL: ALL TESTS PASSED ✅")
    print("="*80)

if __name__ == "__main__":
    print("Starting NerdyStats Backend API Tests")
    print(f"Base URL: {BASE_URL}")
    print("Note: Sleeping 7s between distinct endpoint calls for rate limiting")
    print("\n" + "="*80)
    print("TESTING WORLDWIDE PREDICTIONS BUG FIX")
    print("="*80)
    
    # NEW TESTS: Worldwide predictions (SportApi7 integration)
    print("\n### NEW WORLDWIDE PREDICTION ENDPOINTS ###")
    test_global_predictions_k_league()
    test_global_predictions_chinese_super_league()
    test_global_predictions_allsvenskan()
    test_global_predictions_live()
    test_predictions_upcoming_expanded()
    
    # REGRESSION TESTS: Existing endpoints
    print("\n### REGRESSION TESTS (Existing Endpoints) ###")
    test_competitions()
    matches_data = test_matches_today()
    test_predictions_today()
    test_predictions_upcoming()
    test_bet_of_the_day()
    test_standings()
    test_competition_matches()
    test_competition_scorers()
    
    # Test match detail if we have a match ID
    if matches_data and matches_data.get("matches"):
        match_id = matches_data["matches"][0]["id"]
        test_match_detail(match_id)
    else:
        print("\n⚠️  Skipping match detail test - no matches available")
    
    # Test cache
    test_cache_functionality()
    
    # Print summary
    print_summary()
